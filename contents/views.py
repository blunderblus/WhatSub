import requests
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render

# 1. 검색 화면 렌더링 뷰
def search_page(request):
    return render(request, 'contents/search_page.html')

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

    rapidapi_key = getattr(settings, 'RAPIDAPI_KEY', '')

    # 💡 [변경점 1 & 2] v4 스펙에 맞춰 ID 조합 후 직접 URL에 삽입
    # 예: movie/27205 또는 tv/1396
    formatted_id = f"{media_type}/{tmdb_id}"
    url = f"https://streaming-availability.p.rapidapi.com/shows/{formatted_id}"
    
    querystring = {
        "country": "kr" # 한국 스트리밍 데이터만 요청
    }
    
    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "streaming-availability.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        
        # 만약 API 키 오류나 한도 초과 등 http 에러가 나면 파이썬 에러로 잡아줌
        response.raise_for_status() 
        
        data = response.json()
        providers = []
        
        # 💡 [변경점 3] v4는 최상위가 딕셔너리로 내려옴
        if isinstance(data, dict) and 'streamingOptions' in data:
            # kr(한국)의 스트리밍 옵션 리스트를 가져옴 (없으면 빈 리스트)
            kr_options = data.get('streamingOptions', {}).get('kr', [])
            
            for option in kr_options:
                providers.append({
                    'service': option.get('service', {}).get('name'),
                    'type': option.get('type'),
                    'expires_on': option.get('expiresOn'), # 만료일!
                    'link': option.get('link')
                })
                
        return JsonResponse({'providers': providers}, json_dumps_params={'ensure_ascii': False})

    except requests.exceptions.HTTPError as err:
        # 404(작품 없음) 등 HTTP 에러 발생 시 처리
        if response.status_code == 404:
            return JsonResponse({'providers': []}, json_dumps_params={'ensure_ascii': False})
        return JsonResponse({'error': f"API HTTP 에러: {err}"}, status=response.status_code)
        
    except Exception as e:
        return JsonResponse({'error': f"서버 에러: {str(e)}"}, status=500)