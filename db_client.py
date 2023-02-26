from models import db, User, BaseModel


def prepare_db(owner_id: int, owner_full_name: str):
    """Создает базу данных. Регистрирует владельца как единственного администратора"""
    db.create_tables([User])

    User.update({'is_admin': False}). \
        where(User.is_admin, User.id != owner_id). \
        execute()

    User.get_or_create(
        id=owner_id,
        defaults={
            'full_name': owner_full_name,
            'is_admin': True
        }
    )


def check_user_registration(user_id: int) -> bool:
    """Проверяет зарегистрирован ли пользователь"""
    return User.get_or_none(User.id == user_id)


def create_user(user_id: int, user_full_name: str) -> BaseModel:
    """Регистрирует пользователя в базе"""
    return User.create(id=user_id, full_name=user_full_name)


def get_admin_id() -> int:
    admin = User.get(User.is_admin)
    return admin.id
