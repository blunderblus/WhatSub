"""LLM-assigned user taste title badges (habit + genre)."""

TASTE_TITLE_HABITS = [
    '#가성비_마스터',
    '#프리미엄_단독러',
    '#구독_정주행러',
    '#플랫폼_유목민',
    '#몰아보기_중독',
    '#취향_확신범',
    '#콘텐츠_탐험가',
]

TASTE_TITLE_GENRES = [
    '#블록buster_시네필',
    '#로코·감성_로맨티스트',
    '#장르물·스릴러_매니아',
    '#다큐·지식_탐구자',
    '#예능·쇼_플레이어',
    '#애니·판타지_몽상가',
    '#음악·공연_라이브러리',
]

_GENRE_ID_HINTS = {
    28: '#블록buster_시네필',
    12: '#블록buster_시네필',
    10749: '#로코·감성_로맨티스트',
    10751: '#로코·감성_로맨티스트',
    9648: '#장르물·스릴러_매니아',
    53: '#장르물·스릴러_매니아',
    27: '#장르물·스릴러_매니아',
    99: '#다큐·지식_탐구자',
    36: '#다큐·지식_탐구자',
    16: '#애니·판타지_몽상가',
    878: '#애니·판타지_몽상가',
    10765: '#애니·판타지_몽상가',
    35: '#예능·쇼_플레이어',
    10402: '#음악·공연_라이브러리',
}


def taste_titles_prompt_block() -> str:
    habits = '\n'.join(f'  - {title}' for title in TASTE_TITLE_HABITS)
    genres = '\n'.join(f'  - {title}' for title in TASTE_TITLE_GENRES)
    return (
        'Assign exactly ONE consumption-habit title (taste_title_habit) from:\n'
        f'{habits}\n'
        'Assign exactly ONE content-genre title (taste_title_genre) from:\n'
        f'{genres}\n'
        'Return the exact strings including the # prefix.'
    )


def normalize_taste_title(value, allowed):
    text = (value or '').strip()
    if text in allowed:
        return text
    for item in allowed:
        if item.lstrip('#') == text.lstrip('#'):
            return item
    return ''


def fallback_taste_titles(*, consumption_habits=None, platform_criteria=None, genre_weights=None):
    habits = consumption_habits or {}
    criteria = platform_criteria or []
    weights = genre_weights or {}

    top_genre = None
    top_weight = -1.0
    for gid, weight in weights.items():
        try:
            val = float(weight)
            key = int(gid)
        except (TypeError, ValueError):
            continue
        if val > top_weight:
            top_weight = val
            top_genre = key

    genre = _GENRE_ID_HINTS.get(top_genre, '#블록buster_시네필')
    if genre not in TASTE_TITLE_GENRES:
        genre = TASTE_TITLE_GENRES[0]
    if habits.get('documentary_heavy'):
        genre = '#다큐·지식_탐구자'

    if 'price' in criteria and 'quality' not in criteria:
        habit = '#가성비_마스터'
    elif 'quality' in criteria and 'price' not in criteria:
        habit = '#프리미엄_단독러'
    elif habits.get('binge'):
        habit = '#몰아보기_중독'
    elif habits.get('family'):
        habit = '#구독_정주행러'
    elif len(criteria) >= 3:
        habit = '#플랫폼_유목민'
    else:
        habit = '#취향_확신범'

    if habit not in TASTE_TITLE_HABITS:
        habit = TASTE_TITLE_HABITS[0]
    return habit, genre


def resolve_taste_titles_from_llm(result, *, consumption_habits=None, platform_criteria=None, genre_weights=None):
    habit = normalize_taste_title(result.get('taste_title_habit'), TASTE_TITLE_HABITS)
    genre = normalize_taste_title(result.get('taste_title_genre'), TASTE_TITLE_GENRES)
    if habit and genre:
        return habit, genre
    fallback_habit, fallback_genre = fallback_taste_titles(
        consumption_habits=consumption_habits,
        platform_criteria=platform_criteria,
        genre_weights=genre_weights,
    )
    return habit or fallback_habit, genre or fallback_genre
