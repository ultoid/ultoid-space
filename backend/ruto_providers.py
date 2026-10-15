import logging
import os
from dataclasses import dataclass

import requests
from google import genai
from google.genai import errors

logger = logging.getLogger(__name__)

GEMINI_MODEL_OPTIONS = (
    {'id': 'gemma-4-26b-a4b-it', 'name': 'Gemma 4 26B A4B IT'},
    {'id': 'gemma-4-31b-it', 'name': 'Gemma 4 31B IT'},
)


@dataclass
class ProviderResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class ProviderError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class ProviderConfigurationError(ProviderError):
    pass


class GeminiProvider:
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model

    def generate_reply(self, system_prompt, messages):
        transcript = '\n\n'.join(
            f"{'User' if message['role'] == 'user' else 'Ruto'}:\n{message['content']}"
            for message in messages
        )
        try:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model,
                contents=f"{system_prompt}\n\nRiwayat percakapan:\n{transcript}",
            )
        except errors.APIError as exc:
            if exc.code == 429:
                status = f' ({exc.status})' if exc.status else ''
                detail = ' '.join(str(exc.message or '').split())[:500]
                if detail:
                    message = (
                        f'Google menolak request untuk model "{self.model}" '
                        f'(HTTP 429{status}): {detail}'
                    )
                else:
                    message = (
                        f'Google menolak request untuk model "{self.model}" '
                        f'(HTTP 429{status}). Periksa detail kuota atau batas request '
                        'model ini di Google AI Studio.'
                    )
            elif exc.code in (401, 403):
                message = 'Gemini menolak autentikasi. Periksa GEMINI_API_KEY dan akses project di AI Studio.'
            elif exc.code == 404:
                message = f'Model Gemini "{self.model}" tidak ditemukan atau tidak tersedia untuk API key ini.'
            elif exc.code == 400:
                message = 'Gemini menolak format atau isi request (HTTP 400).'
            elif exc.code >= 500:
                message = f'Layanan Gemini sedang bermasalah (HTTP {exc.code}). Coba lagi nanti.'
            else:
                message = f'Gemini gagal memproses request (HTTP {exc.code}).'
            logger.warning(
                'Ruto Gemini API error: model=%s HTTP=%s status=%s',
                self.model,
                exc.code,
                exc.status,
            )
            raise ProviderError(message, status_code=exc.code) from exc
        except Exception as exc:
            error_type = type(exc).__name__
            if 'timeout' in error_type.lower():
                message = 'Koneksi ke Gemini timeout. Coba kirim ulang pesan.'
            elif 'connect' in error_type.lower() or 'transport' in error_type.lower():
                message = 'Tidak dapat terhubung ke Gemini. Periksa koneksi server.'
            else:
                message = f'Gemini gagal memproses request ({error_type}). Periksa log server.'
            logger.warning('Ruto Gemini request failed: %s', error_type)
            raise ProviderError(message) from exc
        if not response.text or not response.text.strip():
            raise ProviderError('Provider AI mengembalikan jawaban kosong.')
        usage = response.usage_metadata
        input_tokens = getattr(usage, 'prompt_token_count', 0) or 0
        output_tokens = getattr(usage, 'candidates_token_count', 0) or 0
        total_tokens = getattr(usage, 'total_token_count', 0) or input_tokens + output_tokens
        return ProviderResponse(
            text=response.text.strip(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )


class OpenAICompatibleProvider:
    def __init__(self, api_key, model, base_url):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip('/')

    def generate_reply(self, system_prompt, messages):
        url = f'{self.base_url}/chat/completions'
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                *messages,
            ],
            'max_tokens': 2048,
        }
        try:
            response = requests.post(
                url,
                json=payload,
                headers={'Authorization': f'Bearer {self.api_key}'},
                timeout=(10, 120),
            )
            response.raise_for_status()
            data = response.json()
            answer = data['choices'][0]['message']['content']
            usage = data.get('usage') or {}
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code in (401, 403):
                message = 'Provider menolak autentikasi. Periksa RUTO_API_KEY dan akses akun Groq.'
            elif status_code == 404:
                message = f'Model "{self.model}" atau endpoint Groq tidak ditemukan atau tidak tersedia.'
            elif status_code == 429:
                message = 'Batas penggunaan Groq tercapai. Periksa limit dan penggunaan di Groq Console.'
            elif status_code == 413:
                message = (
                    'Konteks request terlalu besar untuk Groq (HTTP 413). '
                    'Ruto hanya mengirim bagian memori, skill, dan riwayat yang relevan; '
                    'coba ringkas pesan atau kurangi sumber GitHub yang diminta.'
                )
            elif status_code and status_code >= 500:
                message = f'Layanan Groq sedang bermasalah (HTTP {status_code}). Coba lagi nanti.'
            elif status_code:
                message = f'Groq menolak request (HTTP {status_code}). Periksa model dan format request.'
            else:
                message = 'Provider AI menolak request.'
            logger.warning('Ruto OpenAI-compatible API error: HTTP %s', status_code)
            raise ProviderError(message) from exc
        except requests.RequestException as exc:
            logger.warning('Ruto OpenAI-compatible request failed: %s', type(exc).__name__)
            raise ProviderError('Tidak dapat terhubung ke Groq. Periksa koneksi server.') from exc
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            logger.warning('Ruto OpenAI-compatible response was invalid: %s', type(exc).__name__)
            raise ProviderError('Provider AI tidak tersedia atau mengembalikan respons tidak valid.') from exc
        if not isinstance(answer, str) or not answer.strip():
            raise ProviderError('Provider AI mengembalikan jawaban kosong.')
        input_tokens = usage.get('prompt_tokens', 0) or 0
        output_tokens = usage.get('completion_tokens', 0) or 0
        total_tokens = usage.get('total_tokens', 0) or input_tokens + output_tokens
        return ProviderResponse(
            text=answer.strip(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )


def get_provider_config(model_override=None):
    provider = os.environ.get('RUTO_PROVIDER', 'gemini').strip().lower()
    model = model_override or os.environ.get('RUTO_MODEL', 'gemini-2.5-flash').strip()
    if not model:
        raise ProviderConfigurationError('RUTO_MODEL belum dikonfigurasi.')

    if provider == 'gemini':
        api_key = os.environ.get('GEMINI_API_KEY', '').strip()
        if not api_key:
            raise ProviderConfigurationError('GEMINI_API_KEY belum dikonfigurasi.')
        return provider, model, GeminiProvider(api_key, model)

    if provider == 'openai-compatible':
        api_key = os.environ.get('RUTO_API_KEY', '').strip()
        base_url = os.environ.get('RUTO_API_BASE_URL', '').strip()
        if not api_key or not base_url:
            raise ProviderConfigurationError('RUTO_API_KEY dan RUTO_API_BASE_URL harus dikonfigurasi.')
        if not base_url.startswith('https://'):
            raise ProviderConfigurationError('RUTO_API_BASE_URL harus menggunakan HTTPS.')
        return provider, model, OpenAICompatibleProvider(api_key, model, base_url)

    raise ProviderConfigurationError('RUTO_PROVIDER harus bernilai gemini atau openai-compatible.')


def provider_status(model_override=None):
    try:
        provider, model, _ = get_provider_config(model_override)
        return {'provider': provider, 'model': model, 'ready': True}
    except ProviderConfigurationError:
        return {
            'provider': os.environ.get('RUTO_PROVIDER', 'gemini').strip().lower(),
            'model': model_override or os.environ.get('RUTO_MODEL', 'gemini-2.5-flash').strip(),
            'ready': False,
        }
