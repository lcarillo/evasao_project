LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'evasao_processing.log',
        },
    },
    'loggers': {
        'dashboard': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}