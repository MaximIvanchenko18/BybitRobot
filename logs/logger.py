import logging

def get_logger(name):
    log_format = '%(asctime)s  %(name)8s  %(levelname)s  %(message)s'
    logging.basicConfig(level=logging.INFO,
                        format=log_format,
                        filename='logs/all_logs.log',
                        filemode='w')
    console = logging.FileHandler('logs/all_logs.log')
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(log_format))
    logging.getLogger(name).addHandler(console)
    return logging.getLogger(name)
