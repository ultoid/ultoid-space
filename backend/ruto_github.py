import base64
import json
import re
import time
from urllib.parse import quote, unquote, urlparse

import requests

MAX_LINKS = 2
MAX_FILE_CHARS = 12000
MAX_CONTEXT_CHARS = 32000
MAX_RETRIEVED_CONTEXT_CHARS = 4000
MAX_FILE_SNIPPET_CHARS = 1500
MAX_API_RESPONSE_BYTES = 1_000_000
TEXT_EXTENSIONS = {
    '.css', '.go', '.html', '.java', '.js', '.json', '.md', '.py',
    '.rs', '.toml', '.ts', '.txt', '.yml', '.yaml',
}
_CACHE_TTL_SECONDS = 600
_cache = {}
CANONICAL_NUSVANIR_REPOSITORY = 'https://github.com/ultoid/nusvanir'


class GitHubReadError(Exception):
    pass


def _extract_urls(text):
    matches = re.findall(
        r'https?://(?:github\.com|raw\.githubusercontent\.com)/[^\s<>"\'`]+',
        text,
        flags=re.IGNORECASE,
    )
    urls = []
    for match in matches:
        url = match.rstrip('.,;!?)]}')
        if url not in urls:
            urls.append(url)
    return urls[:MAX_LINKS]


def _parse_github_url(url):
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'https' or parsed.port not in (None, 443):
        raise GitHubReadError('Tautan GitHub harus menggunakan HTTPS.')
    segments = [unquote(segment) for segment in parsed.path.split('/') if segment]

    if host == 'raw.githubusercontent.com':
        if len(segments) < 4:
            raise GitHubReadError('Tautan raw GitHub tidak memiliki path file yang lengkap.')
        owner, repo, ref = segments[:3]
        path = '/'.join(segments[3:])
        kind = 'file'
    elif host == 'github.com':
        if len(segments) < 2:
            raise GitHubReadError('Tautan GitHub harus mengarah ke repository publik.')
        owner, repo = segments[:2]
        if len(segments) == 2:
            ref, path, kind = '', '', 'repository'
        elif len(segments) >= 4 and segments[2] in ('blob', 'tree'):
            kind = 'file' if segments[2] == 'blob' else 'tree'
            ref, path = segments[3], '/'.join(segments[4:])
            if kind == 'file' and not path:
                raise GitHubReadError('Tautan file GitHub tidak menyertakan nama file.')
        else:
            raise GitHubReadError('Gunakan tautan repository, file (blob), atau folder (tree) GitHub.')
    else:
        raise GitHubReadError('Hanya tautan github.com dan raw.githubusercontent.com yang didukung.')

    if not re.fullmatch(r'[A-Za-z0-9_.-]+', owner) or not re.fullmatch(r'[A-Za-z0-9_.-]+', repo):
        raise GitHubReadError('Nama owner atau repository GitHub tidak valid.')
    if any(segment in ('.', '..') for segment in path.split('/')):
        raise GitHubReadError('Path repository tidak valid.')
    return {
        'owner': owner,
        'repo': repo.removesuffix('.git'),
        'ref': ref,
        'path': path.strip('/'),
        'kind': kind,
        'raw_url': url if host == 'raw.githubusercontent.com' else None,
    }


def _request_bytes(url, accept):
    try:
        response = requests.get(
            url,
            headers={
                'Accept': accept,
                'User-Agent': 'Ruto-V1-public-github-reader',
                'X-GitHub-Api-Version': '2022-11-28',
            },
            timeout=(5, 15),
            allow_redirects=False,
            stream=True,
        )
    except requests.RequestException as exc:
        raise GitHubReadError('Tidak dapat terhubung ke GitHub.') from exc

    try:
        if response.is_redirect:
            raise GitHubReadError('GitHub mengarahkan ke URL lain; periksa kembali tautannya.')
        if response.status_code == 404:
            raise GitHubReadError('Repository atau file GitHub tidak ditemukan atau tidak publik.')
        if response.status_code == 403 and response.headers.get('X-RateLimit-Remaining') == '0':
            raise GitHubReadError('Batas baca publik GitHub tercapai. Coba lagi nanti.')
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise GitHubReadError(f'GitHub menolak permintaan (HTTP {response.status_code}).') from exc

        chunks = []
        size = 0
        for chunk in response.iter_content(chunk_size=16384):
            if not chunk:
                continue
            size += len(chunk)
            if size > MAX_API_RESPONSE_BYTES:
                raise GitHubReadError('Respons GitHub terlalu besar untuk diambil dengan aman.')
            chunks.append(chunk)
        return b''.join(chunks)
    finally:
        response.close()


def _api_json(url):
    data = _request_bytes(url, 'application/vnd.github+json')
    try:
        return json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise GitHubReadError('GitHub mengembalikan metadata yang tidak valid.') from exc


def _file_text(repository, path, ref):
    filename = path.rsplit('/', 1)[-1].lower()
    extension = '.' + filename.rsplit('.', 1)[-1] if '.' in filename else ''
    if extension not in TEXT_EXTENSIONS:
        raise GitHubReadError(f'File {path} bukan format teks yang didukung.')
    if re.search(r'(^|[._-])(secret|credential|token|private|password|\.env)([._-]|$)', filename):
        raise GitHubReadError('File yang berpotensi berisi kredensial tidak diambil.')
    encoded_path = quote(path, safe='/')
    url = f"https://api.github.com/repos/{repository['owner']}/{repository['repo']}/contents/{encoded_path}"
    if ref:
        url += f'?ref={quote(ref, safe="")}'
    data = _api_json(url)
    if not isinstance(data, dict) or data.get('type') != 'file':
        raise GitHubReadError(f'{path} bukan file teks yang dapat dibaca.')
    if data.get('encoding') != 'base64' or not isinstance(data.get('content'), str):
        raise GitHubReadError(f'Format isi file {path} tidak didukung.')
    try:
        content = base64.b64decode(data['content'], validate=False).decode('utf-8', errors='replace')
    except (ValueError, UnicodeDecodeError) as exc:
        raise GitHubReadError(f'File {path} tidak dapat didekode sebagai teks.') from exc
    if len(content) > MAX_FILE_CHARS:
        content = content[:MAX_FILE_CHARS] + '\n[Isi dipotong oleh batas konteks Ruto.]'
    return content


def _default_branch(repository):
    url = f"https://api.github.com/repos/{repository['owner']}/{repository['repo']}"
    metadata = _api_json(url)
    branch = metadata.get('default_branch') if isinstance(metadata, dict) else None
    if not isinstance(branch, str) or not branch:
        raise GitHubReadError('Branch utama repository tidak ditemukan.')
    return branch


def _list_tree(repository, ref, path):
    url = (
        f"https://api.github.com/repos/{repository['owner']}/{repository['repo']}"
        f"/git/trees/{quote(ref, safe='')}?recursive=1"
    )
    data = _api_json(url)
    entries = data.get('tree') if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise GitHubReadError('Struktur file repository tidak dapat dibaca.')
    if data.get('truncated'):
        raise GitHubReadError('Repository terlalu besar untuk ditelusuri sepenuhnya melalui GitHub API.')
    prefix = f'{path}/' if path else ''
    files = []
    for entry in entries:
        entry_path = entry.get('path', '')
        if entry.get('type') != 'blob' or not entry_path.startswith(prefix):
            continue
        relative_path = entry_path[len(prefix):]
        extension = '.' + relative_path.rsplit('.', 1)[-1].lower() if '.' in relative_path else ''
        if extension not in TEXT_EXTENSIONS:
            continue
        if re.search(
            r'(^|[._-])(secret|credential|token|private|password|\.env)([._-]|$)',
            entry_path.rsplit('/', 1)[-1].lower(),
        ):
            continue
        if any(part in ('.git', 'node_modules', 'vendor', 'dist', 'build', '__pycache__') for part in entry_path.split('/')):
            continue
        files.append(entry_path)
    return files


def _rank_paths(paths, query):
    terms = set(re.findall(r'[a-z0-9_]{3,}', query.lower()))
    lore_terms = {
        'nusvanir', 'lore', 'kanon', 'karakter', 'tokoh', 'kisah', 'cerita',
        'story', 'bab', 'adegan', 'chapter', 'scene', 'sejarah', 'kosmologi',
        'sihir', 'magic', 'wilayah', 'region', 'ras', 'monster', 'bestiary',
        'makhluk', 'item', 'senjata', 'hubungan', 'dialog',
    }
    is_lore_query = bool(terms & lore_terms)
    ranked = []
    for path in paths:
        lowered = path.lower()
        name_terms = set(re.findall(r'[a-z0-9_]{3,}', lowered))
        score = len(terms & name_terms)
        if lowered.endswith(('.md', '.txt')):
            score += 2
        if lowered.endswith('readme.md'):
            score += 2
        if lowered.endswith('index.md'):
            score += 1
        if re.search(r'(story|cerita|kisah|chapter|bab|scene|adegan|narrative)', lowered):
            score += 5
        if is_lore_query:
            if re.search(r'(lore|karakter|tokoh)', lowered):
                score += 5
            if lowered.endswith(('.py', '.js', '.ts', '.go', '.java', '.rs')):
                score -= 3
        ranked.append((score, path))
    ranked.sort(key=lambda item: (-item[0], item[1].count('/'), item[1].lower()))
    return [path for _, path in ranked]


def _relevant_text_snippets(content, query, max_chars):
    paragraphs = []
    for part in re.split(r'\n\s*\n', content):
        part = part.strip()
        if len(part) <= MAX_FILE_SNIPPET_CHARS:
            if part:
                paragraphs.append(part)
            continue
        lines = part.splitlines()
        chunk = []
        chunk_chars = 0
        for line in lines:
            if chunk and chunk_chars + len(line) > MAX_FILE_SNIPPET_CHARS:
                paragraphs.append('\n'.join(chunk))
                chunk = []
                chunk_chars = 0
            chunk.append(line)
            chunk_chars += len(line) + 1
        if chunk:
            paragraphs.append('\n'.join(chunk))
    terms = set(re.findall(r'[^\W_]{3,}', query.casefold(), flags=re.UNICODE))
    stop_words = {
        'yang', 'dan', 'atau', 'untuk', 'dari', 'dengan', 'pada', 'dalam',
        'ini', 'itu', 'apa', 'bagaimana', 'jelaskan', 'tentang', 'tolong',
        'the', 'and', 'for', 'with', 'from', 'what', 'how', 'about',
    }
    terms.difference_update(stop_words)
    ranked = []
    for index, paragraph in enumerate(paragraphs):
        paragraph_terms = set(
            re.findall(r'[^\W_]{3,}', paragraph.casefold(), flags=re.UNICODE)
        )
        score = len(terms & paragraph_terms)
        if score:
            ranked.append((score, index, paragraph))
    if not ranked:
        ranked = [(1, index, paragraph) for index, paragraph in enumerate(paragraphs[:2])]
    ranked.sort(key=lambda item: (-item[0], item[1]))

    snippets = []
    used = 0
    for _, _, paragraph in ranked:
        remaining = min(max_chars - used, MAX_FILE_SNIPPET_CHARS)
        if remaining <= 0:
            break
        if len(paragraph) > remaining:
            paragraph = paragraph[:remaining].rsplit(' ', 1)[0].rstrip()
        if paragraph:
            snippets.append(paragraph)
            used += len(paragraph)
    return '\n\n'.join(snippets)


def _canonical_repository(memory, query):
    match = re.search(
        r'^\s*-\s*\*\*Repository (?:utama|Nusvanir):\*\*\s*(https://github\.com/[^\s)]+)',
        memory,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    repository_url = match.group(1) if match else CANONICAL_NUSVANIR_REPOSITORY
    try:
        repository = _parse_github_url(repository_url)
    except GitHubReadError:
        return None
    if repository['kind'] != 'repository':
        return None
    query_terms = set(re.findall(r'[a-z0-9_]{3,}', query.lower()))
    topic_terms = {
        'nusvanir', 'lore', 'kanonis', 'karakter', 'tokoh', 'bestiary',
        'monster', 'ras', 'region', 'sihir', 'github', 'repository', 'repo',
        'cerita', 'kisah', 'sejarah', 'kosmologi', 'wilayah', 'makhluk',
        'item', 'senjata', 'chapter', 'bab', 'adegan', 'story', 'character',
        'history', 'magic', 'worldbuilding',
    }
    if query_terms & topic_terms:
        return repository
    known_names = set(re.findall(r'\b[A-Z][A-Za-z]{2,}\b', memory))
    ignored_names = {
        'Ruto', 'Nusvanir', 'GitHub', 'Repository', 'Memory', 'Google',
        'Bahasa', 'Indonesia', 'Codex', 'Kodex', 'Markdown',
    }
    if any(
        name not in ignored_names and name.lower() in query_terms
        for name in known_names
    ):
        return repository
    return None


def _read_repository(repository, query):
    branch = repository['ref'] or _default_branch(repository)
    linked_path = repository['path']
    if repository['kind'] == 'file':
        paths = [linked_path]
    else:
        paths = _list_tree(
            repository,
            branch,
            linked_path if repository['kind'] == 'tree' else '',
        )
        ranked = _rank_paths(paths, query)
        if repository['kind'] == 'tree':
            paths = ranked[:5]
        else:
            readme = next((path for path in ranked if path.lower().endswith('readme.md')), None)
            other_paths = [path for path in ranked if path != readme]
            paths = ([readme] if readme else []) + other_paths[:4]

    sections = []
    total = 0
    for path in paths[:3]:
        try:
            content = _file_text(repository, path, branch)
        except GitHubReadError:
            if repository['kind'] == 'file':
                raise
            continue
        remaining = MAX_CONTEXT_CHARS - total
        if remaining <= 0:
            break
        content = _relevant_text_snippets(
            content,
            query,
            min(MAX_FILE_SNIPPET_CHARS, remaining),
        )
        if not content:
            continue
        file_url = (
            f"https://github.com/{repository['owner']}/{repository['repo']}"
            f"/blob/{quote(branch, safe='')}/{quote(path, safe='/')}"
        )
        section = f"### {path}\nSource: {file_url}\n\n{content}"
        sections.append(section)
        total += len(section)
    if not sections:
        raise GitHubReadError('Tidak ada file teks yang cocok untuk dibaca di repository ini.')
    return '\n\n'.join(sections)[:MAX_RETRIEVED_CONTEXT_CHARS]


def _read_link(url, query):
    repository = _parse_github_url(url)
    cache_key = f'{url}|{query[:120]}'
    now = time.monotonic()
    cached = _cache.get(cache_key)
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    if repository['raw_url']:
        data = _request_bytes(repository['raw_url'], 'text/plain')
        content = data.decode('utf-8', errors='replace')
        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS] + '\n[Isi dipotong oleh batas konteks Ruto.]'
        content = _relevant_text_snippets(
            content,
            query,
            MAX_FILE_SNIPPET_CHARS,
        )
        result = f"### {repository['path']}\nSource: {url}\n\n{content}"
    else:
        result = _read_repository(repository, query)
    if len(_cache) >= 64:
        oldest = min(_cache, key=lambda key: _cache[key][0])
        _cache.pop(oldest, None)
    _cache[cache_key] = (now, result)
    return result


def fetch_github_context(user_text, memory):
    urls = _extract_urls(user_text)
    if not urls:
        repository = _canonical_repository(memory, user_text)
        if repository:
            urls = [f"https://github.com/{repository['owner']}/{repository['repo']}"]
    if not urls:
        return ''

    sections = []
    for url in urls:
        try:
            sections.append(_read_link(url, user_text))
        except GitHubReadError as exc:
            sections.append(f"### Gagal membaca {url}\n{exc}")
        if sum(map(len, sections)) >= MAX_CONTEXT_CHARS:
            break
    return '\n\n'.join(sections)[:MAX_RETRIEVED_CONTEXT_CHARS]
