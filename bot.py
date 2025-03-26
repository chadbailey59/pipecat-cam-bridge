#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import asyncio
import os

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.gstreamer.pipeline_source import GStreamerPipelineSource
from pipecat.processors.logger import FrameLogger
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecatcloud.agent import DailySessionArguments
load_dotenv(override=True)


async def main(args: DailySessionArguments):    

    logger.debug("Starting bot in room: {}", args.room_url)

    async with aiohttp.ClientSession() as session:
        transport = DailyTransport(
            args.room_url,
            args.token,
            "bot",
            DailyParams(
                audio_out_enabled=True,
                audio_out_is_live=True,
                camera_out_enabled=True,
                camera_out_is_live=True,
                camera_out_width=1280,
                camera_out_height=720,
                transcription_enabled=False,
                vad_enabled=False,
            ),
        )
        # camera_processor = CameraProcessor(camera_url, log)
        """
        gst = GStreamerPipelineSource(
            # pipeline='videotestsrc ! capsfilter caps="video/x-raw,width=1280,height=720,framerate=30/1"',
            pipeline=f"rtspsrc location={os.getenv("CAMERA_RTSP_URL")} latency=0",
            # pipeline=f"rtspsrc location={os.getenv("CAMERA_RTSP_URL")} latency=0 buffer-mode=auto ! rtpjitterbuffer ! rtph264depay ! avdec_h264 ! videoconvert ! video/x-raw,width=1280,height=720 ! autovideosink",
            out_params=GStreamerPipelineSource.OutputParams(
                video_width=1280,
                video_height=720,
            ),
        )
        """

        gst = GStreamerPipelineSource(
            pipeline=f"rtspsrc location={os.getenv('CAMERA_RTSP_URL')} latency=0 ! rtph264depay ! decodebin ! videoconvert ! video/x-raw,format=RGB ! appsink name=appsink sync=false"
        )

        fl = FrameLogger("After camera processor")
        pipeline = Pipeline(
            [
                # camera_processor,
                gst,
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
            logger.info("First participant joined: {}", participant["id"])

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            logger.info("Participant left: {}", participant)
            await task.cancel()

        # Start the camera capture task before running the pipeline
        # CB: I think the FrameProcessor calls start for us
        # await camera_processor.start()

        runner = PipelineRunner()
        await runner.run(task)


async def bot(args: DailySessionArguments):
    """Main bot entry point compatible with the FastAPI route handler.

    Args:
        config: The configuration object from the request body
        room_url: The Daily room URL
        token: The Daily room token
        session_id: The session ID for logging
        session_logger: The session-specific logger
    """
    logger.info(f"Bot process initialized {args.room_url} {args.token}")
    logger.info(f"Bot config {args}")

    try:
        await main(args)
        logger.info("Bot process completed")
    except Exception as e:
        logger.exception(f"Error in bot process: {str(e)}")
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
        args = DailySessionArguments(room_url=room_url, token=token, session_id=None, body=None)
        # webbrowser.open(room_url)
        await main(args)


if LOCAL_RUN and __name__ == "__main__":
    asyncio.run(local_main())
