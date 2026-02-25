from models.mongo import Message, Session


class DataBase:
    def create_session(self, name: str):
        session = Session(session_name=name)
        session.save()
        return session

    def fetch_session(self, name: str):
        session = Session.__objects(session_name=name).first()
        return session

    def fetch_all_session(self):
        sessions = Session.__objects()
        return list(sessions)
