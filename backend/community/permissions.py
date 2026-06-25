def is_staff_user(user):
    return bool(getattr(user, 'is_authenticated', False) and getattr(user, 'is_staff', False))


def can_manage_post(user, post):
    return bool(
        getattr(user, 'is_authenticated', False)
        and (post.author_id == user.id or is_staff_user(user))
    )


def can_manage_comment(user, comment):
    return bool(
        getattr(user, 'is_authenticated', False)
        and (comment.author_id == user.id or is_staff_user(user))
    )
