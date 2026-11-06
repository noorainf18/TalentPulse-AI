"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import {
  ConnectionState,
  Room,
  RoomEvent,
  Track,
  createLocalAudioTrack,
  type RemoteParticipant,
  type RemoteTrack,
  type RemoteTrackPublication,
} from "livekit-client";

import CandidateInterviewLayout from "@/components/interview/CandidateInterviewLayout";
import type { InterviewPhase } from "@/components/interview/CandidateInterviewLayout";
import NeuralBackground from "@/components/effects/NeuralBackground";
import { fetchVoiceJoin, fetchVoiceSessionBrief } from "@/lib/api";
import type { VoiceSessionBrief } from "@/lib/types";

export default function CandidateVoiceInterviewPage() {
  const params = useParams<{ token: string }>();
  const token = params?.token ?? "";
  const roomRef = useRef<Room | null>(null);
  const remoteAudioRef = useRef<HTMLDivElement | null>(null);
  const [phase, setPhase] = useState<InterviewPhase>("idle");
  const [connLabel, setConnLabel] = useState<string>("");
  const [micOn, setMicOn] = useState(true);
  const [sessionBrief, setSessionBrief] = useState<VoiceSessionBrief | null>(null);
  const [briefLoading, setBriefLoading] = useState(false);
  const [briefError, setBriefError] = useState<string | null>(null);
  /** Question IDs the agent has finished reading aloud (LiveKit data); order = reveal order. */
  const [revealedQuestionIds, setRevealedQuestionIds] = useState<string[]>([]);
  /** After disconnect, show full question recap from API. */
  const [postCallRecap, setPostCallRecap] = useState(false);
  const wasConnectedRef = useRef(false);

  const teardown = useCallback(async () => {
    const r = roomRef.current;
    roomRef.current = null;
    if (r) {
      r.removeAllListeners();
      await r.disconnect();
    }
  }, []);

  useEffect(() => {
    return () => {
      void teardown();
    };
  }, [teardown]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setBriefLoading(true);
    setBriefError(null);
    void fetchVoiceSessionBrief(token)
      .then((data) => {
        if (!cancelled) {
          setSessionBrief(data);
          setBriefError(null);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setBriefError(e instanceof Error ? e.message : "Could not load session.");
        }
      })
      .finally(() => {
        if (!cancelled) setBriefLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (phase !== "connected" || !token) return;
    const id = window.setInterval(() => {
      void fetchVoiceSessionBrief(token)
        .then(setSessionBrief)
        .catch(() => {
          /* keep last good brief while live */
        });
    }, 4000);
    return () => window.clearInterval(id);
  }, [phase, token]);

  async function connect() {
    if (!token) return;
    setPhase("joining");
    setConnLabel("Connecting to LiveKit…");
    setPostCallRecap(false);
    setRevealedQuestionIds([]);
    wasConnectedRef.current = false;
    try {
      await teardown();
      const data = await fetchVoiceJoin(token);
      const room = new Room({ adaptiveStream: true, dynacast: true });
      roomRef.current = room;

      const INTERVIEW_DATA_TOPIC = "tp_interview";

      room.on(RoomEvent.DataReceived, (payload: Uint8Array, participant, _kind, topic) => {
        if (topic !== INTERVIEW_DATA_TOPIC) return;
        if (!participant || participant.identity === room.localParticipant.identity) return;
        let msg: { type?: string; question_id?: string };
        try {
          const text = new TextDecoder().decode(payload);
          msg = JSON.parse(text) as { type?: string; question_id?: string };
        } catch {
          return;
        }
        if (msg.type !== "question_prompted" || !msg.question_id) return;
        setRevealedQuestionIds((prev) =>
          prev.includes(msg.question_id!) ? prev : [...prev, msg.question_id!],
        );
      });

      room.on(RoomEvent.ConnectionStateChanged, (s: ConnectionState) => {
        if (s === ConnectionState.Connected) {
          wasConnectedRef.current = true;
          setPhase("connected");
          setConnLabel("You’re in. Listen for the AI interviewer, then answer when prompted.");
        }
        if (s === ConnectionState.Disconnected) {
          setPhase("idle");
          setConnLabel("Disconnected.");
          if (wasConnectedRef.current) setPostCallRecap(true);
        }
      });

      room.on(RoomEvent.Disconnected, () => {
        setPhase("idle");
        setConnLabel("Session ended.");
        if (wasConnectedRef.current) setPostCallRecap(true);
      });

      const attachRemoteAudio = (
        track: RemoteTrack,
        _publication: RemoteTrackPublication,
        _participant: RemoteParticipant,
      ) => {
        if (track.kind !== Track.Kind.Audio) return;
        const parent = remoteAudioRef.current;
        if (!parent) return;
        const audioEl = track.attach();
        parent.appendChild(audioEl);
      };

      const detachRemoteAudio = (track: RemoteTrack) => {
        if (track.kind !== Track.Kind.Audio) return;
        track.detach();
      };

      room.on(RoomEvent.TrackSubscribed, attachRemoteAudio);
      room.on(RoomEvent.TrackUnsubscribed, detachRemoteAudio);

      const serverUrl =
        data.livekit_server_url || process.env.NEXT_PUBLIC_LIVEKIT_URL || "";
      if (!serverUrl) {
        throw new Error(
          "LiveKit server URL missing. Set LIVEKIT_URL on the API or NEXT_PUBLIC_LIVEKIT_URL for the UI.",
        );
      }
      await room.connect(serverUrl, data.livekit_token);
      await room.startAudio();

      for (const participant of room.remoteParticipants.values()) {
        participant.audioTrackPublications.forEach((pub) => {
          if (pub.track) {
            attachRemoteAudio(pub.track, pub, participant);
          }
        });
      }

      const track = await createLocalAudioTrack();
      await room.localParticipant.publishTrack(track);
      setMicOn(true);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Could not join the interview.";
      toast.error(msg);
      setPhase("error");
      setConnLabel(msg);
      await teardown();
    }
  }

  async function toggleMic() {
    const room = roomRef.current;
    if (!room) return;
    const next = !micOn;
    await room.localParticipant.setMicrophoneEnabled(next);
    setMicOn(next);
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#060d14] text-[#e2f0f8]">
      <NeuralBackground />
      <div className="pointer-events-none fixed inset-0 z-[3]">
        <div className="absolute -top-32 left-1/4 h-[500px] w-[500px] rounded-full bg-cyan-500/[0.04] blur-[120px]" />
        <div className="absolute bottom-0 right-1/4 h-[400px] w-[400px] rounded-full bg-teal-400/[0.035] blur-[100px]" />
      </div>

      <CandidateInterviewLayout
        phase={phase}
        connLabel={connLabel}
        micOn={micOn}
        hasToken={Boolean(token)}
        remoteAudioRef={remoteAudioRef}
        sessionBrief={sessionBrief}
        briefLoading={briefLoading}
        briefError={briefError}
        revealedQuestionIds={revealedQuestionIds}
        postCallRecap={postCallRecap}
        onJoin={() => void connect()}
        onToggleMic={() => void toggleMic()}
        onLeave={() => void teardown().then(() => setPhase("idle"))}
        onRetry={() => {
          setPhase("idle");
          setConnLabel("");
        }}
      />
    </div>
  );
}
