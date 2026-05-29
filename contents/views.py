import requests
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render

# 1. 검색 화면 렌더링 뷰
def search_page(request):
    return render(request, 'contents/search_page.html')


def movie_list_page(request):
    return render(request, 'contents/movie_list.html', {
        'media_type': 'movie',
        'content_label': '영화',
        'content_label_en': 'Movies',
        'list_api_url': '/contents/movie_list/',
        'genres_api_url': '/contents/genres/',
        'detail_base_url': '/contents/movies/',
    })


def movie_detail_page(request, tmdb_id):
    return render(request, 'contents/movie_detail.html', {
        'tmdb_id': tmdb_id,
        'media_type': 'movie',
        'content_label': '영화',
        'content_label_en': 'Movies',
        'detail_api_url': f'/contents/movie_detail/{tmdb_id}/',
        'list_url': '/contents/movies/',
    })


def show_list_page(request):
    return render(request, 'contents/movie_list.html', {
        'media_type': 'tv',
        'content_label': '드라마',
        'content_label_en': 'Shows',
        'list_api_url': '/contents/show_list/',
        'genres_api_url': '/contents/show_genres/',
        'detail_base_url': '/contents/shows/',
    })


def show_detail_page(request, tmdb_id):
    return render(request, 'contents/movie_detail.html', {
        'tmdb_id': tmdb_id,
        'media_type': 'tv',
        'content_label': '드라마',
        'content_label_en': 'Shows',
        'detail_api_url': f'/contents/show_detail/{tmdb_id}/',
        'list_url': '/contents/shows/',
    })


def tmdb_genres(request):
    return _tmdb_genres('movie')


def tmdb_show_genres(request):
    return _tmdb_genres('tv')


def _tmdb_genres(media_type):
    url = f'https://api.themoviedb.org/3/genre/{media_type}/list'
    params = {
        'api_key': settings.TMDB_API_KEY,
        'language': 'ko-KR',
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return JsonResponse({'genres': data.get('genres', [])}, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def tmdb_movie_list(request):
    return _tmdb_discover(request, 'movie')


def tmdb_show_list(request):
    return _tmdb_discover(request, 'tv')


def _tmdb_discover(request, media_type):
    genre_id = request.GET.get('genre')
    page = request.GET.get('page', 1)

    url = f'https://api.themoviedb.org/3/discover/{media_type}'
    params = {
        'api_key': settings.TMDB_API_KEY,
        'language': 'ko-KR',
        'include_adult': 'false',
        'sort_by': 'popularity.desc',
        'watch_region': 'KR',
        'page': page,
    }

    if genre_id:
        params['with_genres'] = genre_id

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        movies = []
        for item in data.get('results', []):
            movies.append({
                'tmdb_id': item.get('id'),
                'title': item.get('title') or item.get('name') or item.get('original_title') or item.get('original_name'),
                'overview': item.get('overview') or '줄거리 정보가 아직 없습니다.',
                'release_date': item.get('release_date') or item.get('first_air_date') or '',
                'rating': item.get('vote_average') or 0,
                'poster_url': (
                    f"https://image.tmdb.org/t/p/w300{item.get('poster_path')}"
                    if item.get('poster_path')
                    else None
                ),
            })

        return JsonResponse({
            'page': data.get('page', 1),
            'total_pages': data.get('total_pages', 1),
            'results': movies,
        }, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def tmdb_movie_detail(request, tmdb_id):
    return _tmdb_content_detail(request, tmdb_id, 'movie')


def tmdb_show_detail(request, tmdb_id):
    return _tmdb_content_detail(request, tmdb_id, 'tv')


def _tmdb_content_detail(request, tmdb_id, media_type):
    try:
        detail = _tmdb_get(f'https://api.themoviedb.org/3/{media_type}/{tmdb_id}', {
            'append_to_response': 'credits',
            'language': 'ko-KR',
        })

        cast = []
        for person in detail.get('credits', {}).get('cast', [])[:12]:
            cast.append({
                'name': person.get('name'),
                'character': person.get('character') or '',
                'profile_url': _tmdb_image(person.get('profile_path'), 'w185'),
            })

        runtime = detail.get('runtime') or 0
        if not runtime and detail.get('episode_run_time'):
            runtime = detail.get('episode_run_time')[0]

        movie = {
            'tmdb_id': detail.get('id'),
            'title': detail.get('title') or detail.get('name') or detail.get('original_title') or detail.get('original_name'),
            'original_title': detail.get('original_title') or detail.get('original_name') or '',
            'overview': detail.get('overview') or '줄거리 정보가 아직 없습니다.',
            'release_date': detail.get('release_date') or detail.get('first_air_date') or '',
            'runtime': runtime,
            'rating': detail.get('vote_average') or 0,
            'genres': detail.get('genres', []),
            'poster_url': _tmdb_image(detail.get('poster_path'), 'w500'),
            'backdrop_url': _tmdb_image(detail.get('backdrop_path'), 'w1280'),
            'cast': cast,
        }

        raw_streaming_data = _fetch_streaming_availability(tmdb_id, media_type)
        payload = {
            'movie': movie,
            'providers': _parse_streaming_providers(raw_streaming_data),
        }
        if request.GET.get('debug_raw') == '1':
            payload['raw_streaming_data'] = raw_streaming_data
        return JsonResponse(payload, json_dumps_params={'ensure_ascii': False})
    except requests.exceptions.HTTPError as err:
        status_code = err.response.status_code if err.response is not None else 500
        return JsonResponse({'error': f'TMDB API HTTP 에러: {err}'}, status=status_code)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def _tmdb_get(url, params=None):
    request_params = {
        'api_key': settings.TMDB_API_KEY,
        **(params or {}),
    }
    response = requests.get(url, params=request_params)
    response.raise_for_status()
    return response.json()


def _tmdb_image(path, size):
    if not path:
        return None
    return f'https://image.tmdb.org/t/p/{size}{path}'


def _get_streaming_providers(tmdb_id, media_type):
    data = _fetch_streaming_availability(tmdb_id, media_type)
    return _parse_streaming_providers(data)


def _fetch_streaming_availability(tmdb_id, media_type):
    rapidapi_key = getattr(settings, 'RAPIDAPI_KEY', '')
    formatted_id = f"{media_type}/{tmdb_id}"
    url = f"https://streaming-availability.p.rapidapi.com/shows/{formatted_id}"
    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "streaming-availability.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params={"country": "kr"})
    if response.status_code == 404:
        return {}
    response.raise_for_status()

    data = response.json()
    print("=== Streaming Availability 원본 JSON ===")
    print(data, flush=True)
    return data


def _parse_streaming_providers(data):
    providers = []
    seen = set()
    addon_added = False
    if isinstance(data, dict) and 'streamingOptions' in data:
        kr_options = data.get('streamingOptions', {}).get('kr', [])
        for option in kr_options:
            service = option.get('service', {})
            addon = option.get('addon') or {}
            provider_type = option.get('type')
            if provider_type == 'addon':
                if addon_added:
                    continue
                addon_added = True

            service_id = service.get('id') or service.get('name')
            addon_id = addon.get('id') or addon.get('name') or ''
            dedupe_key = (service_id, provider_type, addon_id)

            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            service_name = service.get('name')
            addon_name = addon.get('name')

            providers.append({
                'service': service_name,
                'service_id': service.get('id'),
                'addon': addon_name,
                'display_name': service_name,
                'type': provider_type,
                'type_label': _provider_type_label(provider_type),
                'expires_on': option.get('expiresOn'),
                'link': option.get('videoLink') or option.get('link'),
                'icon_url': _find_image_url(service),
            })

    priority = {'subscription': 0, 'free': 1, 'ads': 2, 'rent': 3, 'buy': 4, 'addon': 5}
    return sorted(providers, key=lambda provider: priority.get(provider.get('type'), 99))


def _provider_type_label(provider_type):
    labels = {
        'subscription': '구독',
        'rent': '대여',
        'buy': '구매',
        'free': '무료',
        'ads': '광고 포함',
    }
    return labels.get(provider_type, '기타')


def _find_image_url(value):
    if isinstance(value, str) and value.startswith('http'):
        return value
    if isinstance(value, dict):
        for key in ('lightThemeImage', 'darkThemeImage', 'whiteImage', 'imageUrl', 'url'):
            found = _find_image_url(value.get(key))
            if found:
                return found
        for child in value.values():
            found = _find_image_url(child)
            if found:
                return found
    if isinstance(value, list):
        for child in value:
            found = _find_image_url(child)
            if found:
                return found
    return None

# 2. 영화/TV 검색 API (TMDB)
def tmdb_search(request):
    query = request.GET.get('query')
    if not query:
        return JsonResponse({'results': []})

    url = 'https://api.themoviedb.org/3/search/multi'
    params = {
        'api_key': settings.TMDB_API_KEY,
        'query': query,
        'language': 'ko-KR',
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        results = []

        for item in data.get('results', []):
            if item.get('media_type') not in ['movie', 'tv']:
                continue

            results.append({
                'tmdb_id': item.get('id'),
                'title': item.get('title') or item.get('name'),
                'media_type': item.get('media_type'),
                'release_date': item.get('release_date') or item.get('first_air_date'),
                'poster_url': (f"https://image.tmdb.org/t/p/w200{item.get('poster_path')}" if item.get('poster_path') else None)
            })
        return JsonResponse({'results': results}, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# 3. 스트리밍 정보 및 만료일 API (RapidAPI)
def api_streaming_info(request):
    tmdb_id = request.GET.get('tmdb_id')
    # TMDB에서 넘어오는 'movie' 또는 'tv' 
    media_type = request.GET.get('media_type')
    
    if not tmdb_id or not media_type:
        return JsonResponse({'error': '파라미터 누락'}, status=400)

    try:
        raw_streaming_data = _fetch_streaming_availability(tmdb_id, media_type)
        payload = {'providers': _parse_streaming_providers(raw_streaming_data)}
        if request.GET.get('debug_raw') == '1':
            payload['raw_streaming_data'] = raw_streaming_data
        return JsonResponse(payload, json_dumps_params={'ensure_ascii': False})

    except requests.exceptions.HTTPError as err:
        # 404(작품 없음) 등 HTTP 에러 발생 시 처리
        status_code = err.response.status_code if err.response is not None else 500
        if status_code == 404:
            return JsonResponse({'providers': []}, json_dumps_params={'ensure_ascii': False})
        return JsonResponse({'error': f"API HTTP 에러: {err}"}, status=status_code)
        
    except Exception as e:
        return JsonResponse({'error': f"서버 에러: {str(e)}"}, status=500)
