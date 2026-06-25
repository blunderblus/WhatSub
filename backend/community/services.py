from .models import CommunityComment, CommunityPost


def create_post(*, author, board, title, content, platform_id=None, flair_tag=''):
    post = CommunityPost.objects.create(
        board=board,
        title=title,
        content=content,
        author=author,
        platform_id=platform_id if platform_id else None,
        flair_tag=flair_tag or '',
    )
    post.comment_count = 0
    return post


def update_post(post, *, title, content):
    post.title = title
    post.content = content
    post.save(update_fields=['title', 'content', 'updated_at'])
    post.comment_count = post.comments.count()
    return post


def create_comment(*, post, author, content):
    return CommunityComment.objects.create(post=post, author=author, content=content)


def update_comment(comment, *, content):
    comment.content = content
    comment.save(update_fields=['content', 'updated_at'])
    return comment


def apply_reaction(model, lookup, user, reaction):
    existing = model.objects.filter(**lookup, user=user).first()
    if not reaction or (existing and existing.reaction == reaction):
        if existing:
            existing.delete()
    elif existing:
        existing.reaction = reaction
        existing.save(update_fields=['reaction', 'updated_at'])
    else:
        model.objects.create(**lookup, user=user, reaction=reaction)


def report_once(model, lookup, user):
    model.objects.get_or_create(**lookup, user=user)
