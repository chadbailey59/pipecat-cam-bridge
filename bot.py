#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import asyncio
import os

import aiohttp
import cv2
from dotenv import load_dotenv
from loguru import logger
from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    Frame,
    OutputImageRawFrame,
    StartFrame,
    SystemFrame,
)
from pipecat.pipeline.pipeline import FrameProcessor, Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import FrameDirection, PipelineParams, PipelineTask
from pipecat.processors.logger import FrameLogger
from pipecat.transports.services.daily import DailyParams, DailyTransport

load_dotenv(override=True)


async def main(room_url: str, token: str, session_logger=None):
    log = session_logger or logger

    log.debug("Starting bot in room: {}", room_url)

    async with aiohttp.ClientSession() as session:
        transport = DailyTransport(
            room_url,
            token,
            "bot",
            DailyParams(
                audio_out_enabled=True,
                camera_out_enabled=True,
                camera_out_is_live=True,
                camera_out_width=1280,
                camera_out_height=720,
                transcription_enabled=False,
                vad_enabled=False,
            ),
        )

        # Initialize camera processor
        camera_url = os.getenv("CAMERA_RTSP_URL")
        if not camera_url:
            log.error("CAMERA_RTSP_URL environment variable not set")
            return

        camera_processor = CameraProcessor(camera_url, log)
        fl = FrameLogger("After camera processor")
        pipeline = Pipeline(
            [
                camera_processor,
                # fl,
                transport.output(),
            ]
        )

        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
                report_only_initial_ttfb=True,
            ),
        )

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            log.info("First participant joined: {}", participant["id"])

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            log.info("Participant left: {}", participant)
            await task.cancel()

        # Start the camera capture task before running the pipeline
        # CB: I think the FrameProcessor calls start for us
        # await camera_processor.start()

        runner = PipelineRunner()
        await runner.run(task)


class CameraProcessor(FrameProcessor):
    def __init__(self, camera_url: str, logger=None):
        super().__init__(name="CameraProcessor")
        self.camera_url = camera_url
        self.log = logger or logger.getLogger(__name__)
        self.cap = None
        self._capture_task = None
        self._running = False

    async def _start(self):
        """Start the camera capture task."""
        print("camera capture start")
        if self._capture_task is not None:
            self.log.warning("Camera capture task is already running")
            return

        await self.setup()
        self._running = True
        self._capture_task = self.create_task(self._capture_frames())
        self.log.info("Started camera capture task")

    async def setup(self):
        """Initialize the camera capture."""
        self.log.info(f"Initializing camera capture from {self.camera_url}")
        self.cap = cv2.VideoCapture(self.camera_url)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera stream at {self.camera_url}")

    async def _capture_frames(self):
        """Continuous task to capture and process frames."""
        while self._running:
            if not self.cap:
                await self.setup()

            ret, frame = self.cap.read()
            if not ret:
                self.log.warning("Failed to read frame from camera")
                await asyncio.sleep(0.1)  # Short delay before retrying
                continue

            # Convert frame to RGB and get raw bytes
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_bytes = cv2.imencode(".png", frame_rgb)[1].tobytes()
            if ret:
                cv2.imshow("MJPEG Stream", frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            else:
                print("Failed to read frame")
                break
            # Create an OutputImageRawFrame
            image_frame = OutputImageRawFrame(
                image=frame_bytes, size=(frame.shape[1], frame.shape[0]), format="png"
            )

            # Push the frame downstream
            await self.push_frame(image_frame)

            # Small delay to control frame rate
            await asyncio.sleep(1 / 30)  # 30 FPS

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process incoming frames. This processor mainly handles frame output via the capture task."""
        await super().process_frame(frame, direction)
        if isinstance(frame, SystemFrame):
            if isinstance(frame, StartFrame):
                await self._start()
            if isinstance(frame, (EndFrame, CancelFrame)):
                await self._stop()
        await self.push_frame(frame, direction)

    async def _stop(self):
        """Clean up resources and stop the capture task."""
        self._running = False
        if self._capture_task:
            await self.cancel_task(self._capture_task)
            self._capture_task = None

        if self.cap:
            self.cap.release()
            self.cap = None


async def bot(config, room_url: str, token: str, session_id=None, session_logger=None):
    """Main bot entry point compatible with the FastAPI route handler.

    Args:
        config: The configuration object from the request body
        room_url: The Daily room URL
        token: The Daily room token
        session_id: The session ID for logging
        session_logger: The session-specific logger
    """
    log = session_logger or logger
    log.info(f"Bot process initialized {room_url} {token}")
    log.info(f"Bot config {config}")

    try:
        await main(room_url, token, session_logger)
        log.info("Bot process completed")
    except Exception as e:
        log.exception(f"Error in bot process: {str(e)}")
        raise


###########################
# for local test run only #
###########################
LOCAL_RUN = os.getenv("LOCAL_RUN")
if LOCAL_RUN:
    import asyncio


async def local_main():
    async with aiohttp.ClientSession() as session:
        # (room_url, token) = await configure(session)
        room_url = os.getenv("DAILY_ROOM")
        token = os.getenv("DAILY_TOKEN")
        logger.warning("_")
        logger.warning("_")
        logger.warning(f"Talk to your voice agent here: {room_url}")
        logger.warning("_")
        logger.warning("_")
        # webbrowser.open(room_url)
        await main(room_url, token)


if LOCAL_RUN and __name__ == "__main__":
    asyncio.run(local_main())
