#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import asyncio
import os
import sys

from dotenv import load_dotenv
from loguru import logger
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.gstreamer.pipeline_source import GStreamerPipelineSource
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecatcloud.agent import DailySessionArguments

load_dotenv(override=True)
logger.add(sys.stderr, level="DEBUG")


async def main(args: DailySessionArguments):
    logger.info(f"Starting bot: args is {args}")
    # Use room url and token from body instead of directly created
    transport = DailyTransport(
        args.body["daily_room_url"],
        args.body["daily_token"],
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
    camera_url = f"rtsp://{args.body['cam_username']}:{args.body['cam_password']}@{args.body['cam_hostname']}/axis-media/media.amp?streamprofile=h264-daily"
    logger.info(f"Connecting to camera at {camera_url}")
    gst = GStreamerPipelineSource(
        pipeline=f"rtspsrc location={camera_url} latency=0 ! rtph264depay ! decodebin ! videoconvert ! video/x-raw,format=RGB ! appsink name=appsink sync=false"
    )

    pipeline = Pipeline(
        [
            gst,
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
    # (room_url, token) = await configure(session)
    room_url = os.getenv("DAILY_ROOM_URL")
    token = os.getenv("DAILY_TOKEN")
    logger.warning("_")
    logger.warning("_")
    logger.warning(f"Talk to your voice agent here: {room_url}")
    logger.warning("_")
    logger.warning("_")
    args = DailySessionArguments(
        room_url=room_url,
        token=token,
        session_id=None,
        body={
            "daily_room_url": room_url,
            "daily_token": token,
            "cam_hostname": os.getenv("CAM_HOSTNAME"),
            "cam_username": os.getenv("CAM_USERNAME"),
            "cam_password": os.getenv("CAM_PASSWORD"),
        },
    )
    # webbrowser.open(room_url)
    await main(args)


if LOCAL_RUN and __name__ == "__main__":
    asyncio.run(local_main())
