import time
from plyer import notification

if __name__ == "__main__":
    while True:
        notification.notify(
            title = "Python ALERT!!!",
            message = "Take a break! Too long working session !!!",
            timeout = 10
        )
        time.sleep(10)