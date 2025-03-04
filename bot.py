#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import os

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
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
                video_out_enabled=True,
                transcription_enabled=False,
                vad_enabled=False,
            ),
        )

        pipeline = Pipeline(
            [
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

        runner = PipelineRunner()

        await runner.run(task)


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
