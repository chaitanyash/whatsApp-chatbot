from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

from app.models import db, SecretSanta, Participant
from flask import current_app


def _send_message(message, number):
    """
    Send a whatsapp message using the twilio Cliente.
    Configure the twilio account SID and TOKEN in the settings file.
    :type message: str
    :param message: text to send
    :type number: str
    :param number: number to send the message
    """
    client = Client(
        current_app.config.TWILIO_ACCOUNT_SID, current_app.config.TWILIO_AUTH_TOKEN
    )

    body = "\n".join(message)

    message = client.messages.create(
        body=body, from_=f"{current_app.config.TWILIO_NUMBER}", to=f"{number}",
    )


def _bot_replay(response):
    """
    Replay a whatsapp message using the MessagingResponse.
    Use this method if you what a direct replay given a client message.
    :type number: str
    :param response: text to send as response
    
    :returns: XML string with the text to response
    """
    resp = MessagingResponse()
    msg = resp.message()
    msg.body("\n".join(response))
    return str(resp)


def process_message(message, number):
    """
    Process the user message and decide witch action hould be made.
    :type message: str
    :param message: user message
    :type number: str
    :param number: user number
    """
    response = []

    # help command
    if message == "help":
        response.append("create: create a new secret santa")
        response.append("run {code}: run the secret santa")
        response.append("cancel {code}: cancel the secret santa")
        response.append("add {name} to {code}: to join the secret santa")
        return _bot_replay(response)

    if message == "create":
        ss = SecretSanta.create(creator_number=number)
        db.session.add(ss)
        db.session.commit()

        response.append("Hey! You created a new Secret Santa!")
        response.append(f"*The Secret Santa code is {ss.id}*")
        response.append("Give to your friends this code.")
        response.append(f"When they finish, texting 'run {ss.id}'.")

        return _bot_replay(response)

    if message.startswith("add "):
        words = message.split()
        participant_name = " ".join(words[1:-2])
        code = int(words[-1].strip())

        ss = SecretSanta.query.filter_by(id=code).first()

        if not ss:
            response.append(f"There is not Secret Santa with code {code}!")
            response.append(
                f"Please, send a message in the form 'add *NAME* to *CODE*'"
            )
            response.append("For example, 'add Bill to 9'")
            return _bot_replay(response)

        participant = Participant(name=participant_name, number=number)
        ss.participants.append(participant)
        db.session.add(participant)
        db.session.commit()

        response.append(f"*{participant_name}* was added!")

        # check if the participant is the creator
        if not number == ss.creator_number:
            _send_message(response, f"{ss.creator_number}")
        return _bot_replay(response)

    if message.startswith("run "):
        code = int(message.split()[-1])
        ss = SecretSanta.query.filter_by(id=code).first()
        if not ss:
            response.append(f"There is not Secret Santa with code {code}!")
            response.append(f"Please, create a new Secret Santa or use a valid code.")
            response.append("Send 'help' if you want see the available commands.")
            return _bot_replay(response)

        if not ss.in_process:
            response.append(f"Secret Santa {ss.id} is not open.")
            return _bot_replay(response)

        result = ss.run()
        db.session.commit()
        for pair in result:
            p1, p2 = pair
            _send_message(
                [f"Hi {p1.name}, you got {p2.name} ({p2.number})!"], f"{p1.number}",
            )

        return _bot_replay(["Secret Santa is done!"])

    if message.startswith("cancel "):
        code = int(message.split()[-1])
        if not code:
            return _bot_replay([f"Please, send a valid code."])

        ss = SecretSanta.query.filter_by(id=code).delete()
        db.session.commit()
        if not ss:
            return _bot_replay([f"There is not Secret Santa with code {code}"])

        return _bot_replay([f"Secret Santa {code} was deleted!"])

    return _bot_replay(["Sorry, I can't help you :("])