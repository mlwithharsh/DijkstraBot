from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dijkstrabot.utils.logger import logger

def start_scheduler(func, cron_expr: str, *args, **kwargs):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(func, CronTrigger.from_crontab(cron_expr), args=args, kwargs=kwargs)
    scheduler.start()
    logger.info("scheduler_started", cron=cron_expr)
    return scheduler
