'''
    Docstring
'''
from app import app
from app import config
from app.utils.log import get_app_logger

logger = get_app_logger()
logger.info('** HLO Deployment engine started **')
logger.info('Development Mode: %s', config.DEV)
logger.info('CB_URL: %s', config.CB_URL)
logger.info('CB_PORT: %s', config.CB_PORT)
# logger.info("REDPANDA BROKER: %s", config.consumer_config['bootstrap.servers'])
# logger.info("GROUP_ID: %s", config.consumer_config['group.id'])
# logger.info("OFFSET_RESET: %s", config.consumer_config['auto.offset.reset'])
logger.info("CONSUMER_TOPIC: %s", config.CONSUMER_TOPIC)
logger.info("TOKEN_URL: %s", config.TOKEN_URL)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
