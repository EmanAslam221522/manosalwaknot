from datetime import UTC, datetime
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai_service import create_action, run_mano
from app.api.deps import current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import ApiError
from app.core.rate_limit import enforce_rate_limit
from app.models import AiAction, AiConversation, AiMessage, Role, User
from app.schemas import ManoActionConfirm, ManoActionResult, ManoMessageIn, ManoMessageOut, ManoResponse, SuggestedActionOut, TranscriptionOut

router = APIRouter(prefix="/ai", tags=["Mano AI"])


def mano_message_out(message: AiMessage) -> ManoMessageOut:
    return ManoMessageOut(id=message.id, role="assistant", content=message.content, created_at=message.created_at, references=message.references)


def suggested_action_out(action: AiAction) -> SuggestedActionOut:
    return SuggestedActionOut(id=action.id, kind=action.kind, label=action.label, summary=action.summary, resource_id=action.resource_id, requires_confirmation=True, expires_at=action.expires_at)


def replay_mano_response(user_message: AiMessage, db: Session) -> ManoResponse:
    assistant = db.scalar(select(AiMessage).where(AiMessage.reply_to_message_id == user_message.id))
    if assistant is None:
        raise ApiError(409, "MESSAGE_IN_PROGRESS", "This message is still being processed. Please try again.")
    actions = db.scalars(select(AiAction).where(AiAction.source_message_id == user_message.id).order_by(AiAction.created_at)).all()
    return ManoResponse(conversation_id=user_message.conversation_id, message=mano_message_out(assistant), suggested_actions=[suggested_action_out(action) for action in actions])


@router.post("/mano/messages", response_model=ManoResponse)
def mano_message(payload: ManoMessageIn, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)) -> ManoResponse:
    enforce_rate_limit(request, "mano_message", 30, 3600, str(user.id))
    authorized_experiences = {entry.role for entry in user.roles}
    if Role.ORGANIZATION in authorized_experiences:
        authorized_experiences.update({Role.RECIPIENT, Role.FOOD_PROVIDER})
    if payload.experience not in {Role.RECIPIENT, Role.FOOD_PROVIDER, Role.VOLUNTEER} or payload.experience not in authorized_experiences:
        raise ApiError(403, "EXPERIENCE_NOT_AUTHORIZED", "This assistant experience is not available for your account.")
    duplicate = db.scalar(select(AiMessage).where(AiMessage.user_id == user.id, AiMessage.client_message_id == payload.client_message_id))
    if duplicate is not None:
        return replay_mano_response(duplicate, db)
    conversation = db.get(AiConversation, payload.conversation_id) if payload.conversation_id else None
    if conversation is not None and conversation.user_id != user.id:
        raise ApiError(404, "CONVERSATION_NOT_FOUND", "This conversation was not found.")
    if conversation is None:
        conversation = AiConversation(user_id=user.id, language=payload.language)
        db.add(conversation)
        db.flush()
    try:
        with db.begin_nested():
            user_message = AiMessage(conversation_id=conversation.id, user_id=user.id, role="user", content=payload.message, client_message_id=payload.client_message_id)
            db.add(user_message)
            db.flush()
    except IntegrityError:
        duplicate = db.scalar(select(AiMessage).where(AiMessage.user_id == user.id, AiMessage.client_message_id == payload.client_message_id))
        if duplicate is None:
            raise ApiError(409, "MESSAGE_IN_PROGRESS", "This message is still being processed. Please try again.")
        return replay_mano_response(duplicate, db)
    result = run_mano(payload.message, payload.language, payload.experience, user, db)
    assistant = AiMessage(conversation_id=conversation.id, user_id=user.id, reply_to_message_id=user_message.id, role="assistant", content=result["response"], references=result.get("references", []))
    db.add(assistant)
    db.flush()
    suggested: list[SuggestedActionOut] = []
    if result.get("action"):
        action = create_action(db, conversation.id, user_message.id, user, result["action"])
        suggested.append(suggested_action_out(action))
    db.commit()
    return ManoResponse(conversation_id=conversation.id, message=mano_message_out(assistant), suggested_actions=suggested)


@router.post("/mano/actions/{action_id}/confirm", response_model=ManoActionResult)
def confirm_action(action_id: UUID, payload: ManoActionConfirm, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)) -> ManoActionResult:
    enforce_rate_limit(request, "mano_action", 20, 3600, str(user.id))
    action = db.scalar(select(AiAction).where(AiAction.id == action_id, AiAction.conversation_id == payload.conversation_id, AiAction.user_id == user.id).with_for_update())
    if action is None:
        raise ApiError(404, "AI_ACTION_NOT_FOUND", "This assistant action was not found.")
    if action.status in {"COMPLETED", "EXPIRED"}:
        if action.idempotency_key != payload.idempotency_key or action.result_message_id is None:
            raise ApiError(409, "AI_ACTION_ALREADY_PROCESSED", "This assistant action was already processed.")
        stored_message = db.get(AiMessage, action.result_message_id)
        if stored_message is None:
            raise ApiError(409, "AI_ACTION_RESULT_UNAVAILABLE", "This assistant action result is unavailable.")
        return ManoActionResult(action_id=action.id, status=action.status, message=mano_message_out(stored_message), resource_type=None, resource_id=None)
    action.status = "EXPIRED" if action.expires_at <= datetime.now(UTC) else "COMPLETED"
    action.idempotency_key = payload.idempotency_key
    content = "This assistant action expired. Please ask Mano again." if action.status == "EXPIRED" else "Draft confirmed. Open the food post flow to complete required safety, pickup, category, and location details. Nothing has been published."
    message = AiMessage(conversation_id=action.conversation_id, user_id=user.id, role="assistant", content=content)
    db.add(message)
    db.flush()
    action.result_message_id = message.id
    db.commit()
    return ManoActionResult(action_id=action.id, status=action.status, message=mano_message_out(message), resource_type=None, resource_id=None)


@router.post("/voice/transcriptions", response_model=TranscriptionOut)
async def transcribe_voice(request: Request, audio: UploadFile = File(...), language: str = Form(...), user: User = Depends(current_user)) -> TranscriptionOut:
    enforce_rate_limit(request, "voice_transcription", 20, 3600, str(user.id))
    if language not in {"en", "ur", "ps", "hno", "pa"}:
        raise ApiError(422, "INVALID_LANGUAGE", "Choose a supported language.")
    if audio.content_type not in {"audio/m4a", "audio/mp4", "audio/webm", "audio/x-m4a"}:
        raise ApiError(422, "INVALID_AUDIO", "Use an M4A or WebM voice recording.")
    content = await audio.read(get_settings().max_upload_bytes + 1)
    if len(content) > get_settings().max_upload_bytes:
        raise ApiError(413, "AUDIO_TOO_LARGE", "The voice recording is too large.")
    settings = get_settings()
    if settings.groq_api_key is None:
        raise ApiError(503, "AI_UNAVAILABLE", "Voice transcription is temporarily unavailable.")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{str(settings.groq_base_url).rstrip('/')}/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.groq_api_key.get_secret_value()}"},
                files={"file": (audio.filename or "voice.webm", content, audio.content_type)},
                data={"model": "whisper-large-v3-turbo", "language": language},
                timeout=httpx.Timeout(40, connect=10),
            )
        response.raise_for_status()
        text = str(response.json()["text"]).strip()
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise ApiError(503, "AI_UNAVAILABLE", "Voice transcription is temporarily unavailable.") from exc
    if not text:
        raise ApiError(422, "NO_SPEECH_DETECTED", "No speech was detected in the recording.")
    return TranscriptionOut(text=text, detected_language=language)
