import {
  AudioModule,
  RecordingPresets,
  setAudioModeAsync,
  useAudioRecorder,
  useAudioRecorderState,
} from 'expo-audio';
import { Mic, Square } from 'lucide-react-native';
import { Platform } from 'react-native';
import { useThemeColor } from 'heroui-native';
import { AppButton } from '@/components/ui/AppButton';
import type { RecordedAudio } from '@/types/mano';

export function VoiceInputButton({
  isDisabled,
  onRecorded,
  onError,
}: {
  isDisabled: boolean;
  onRecorded: (audio: RecordedAudio) => void;
  onError: (message: string) => void;
}) {
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const recorderState = useAudioRecorderState(recorder);
  const accent = useThemeColor('accent');

  const startRecording = async () => {
    try {
      const permission = await AudioModule.requestRecordingPermissionsAsync();
      if (!permission.granted) {
        onError('Microphone permission is needed for voice input. You can still type a message.');
        return;
      }
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      await recorder.prepareToRecordAsync();
      recorder.record();
    } catch {
      onError('Voice input could not start. You can still type a message.');
    }
  };

  const stopRecording = async () => {
    try {
      await recorder.stop();
      await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true });
      if (!recorder.uri) {
        onError('No recording was captured. Please try again or type a message.');
        return;
      }
      onRecorded({
        uri: recorder.uri,
        mimeType: Platform.OS === 'web' ? 'audio/webm' : 'audio/m4a',
      });
    } catch {
      onError('Voice input could not be completed. You can still type a message.');
    }
  };

  const isRecording = recorderState.isRecording;
  return (
    <AppButton
      label={isRecording ? 'Stop' : 'Voice'}
      size="sm"
      variant={isRecording ? 'danger' : 'ghost'}
      isDisabled={isDisabled}
      accessibilityLabel={isRecording ? 'Stop voice recording' : 'Start voice recording'}
      onPress={() => void (isRecording ? stopRecording() : startRecording())}
    >
      {isRecording ? <Square size={16} color={accent} /> : <Mic size={17} color={accent} />}
    </AppButton>
  );
}
