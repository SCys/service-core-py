from urllib.parse import urlencode

from tornado.httpclient import HTTPError

from .log import D, E
from .options import options
from .web import json_fetch

__all__ = ["send_mail"]


async def send_mail(to, subject, content) -> dict:
    """
    send by mailgun

    :param to: send to
    :param subject: email subject
    :param content: email content
    :return:
    ```json
    {
        "message": "Queued. Thank you.",
        "id": "<20111114174239.25659.5817@samples.mailgun.org>"
    }
    ```
    """

    try:
        result = await json_fetch(
            "https://api.mailgun.net/v3/mg.iscys.com/messages",
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            body=urlencode({"from": options.mail_sender, "to": to, "subject": subject, "html": content}),
            # extra params
            auth_username="api",
            auth_password=options.mail_key,
            validate_cert=False,  # DEBUG remove it
        )
    except HTTPError as e:
        E("[mail]mail %s %s error:%s", to, subject, e)
        return

    if result is None:
        return

    D("[mail]mail %s sent:%s", result["id"], result["message"])
    return result
