def should_substitute(minute, stamina):

    if minute > 60 and stamina < 50:
        return True

    return False