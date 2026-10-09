"""Transport an explicitly reviewed preview; never create editorial approval.

The ordinary checkout's site tree remains byte-identical. Preview inputs live
under verification-previews/<id>/ and are added only to the uploaded artifact.
An empty dispatch restores the ordinary site. No network or third-party modules.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
from datetime import datetime
from pathlib import Path, PurePosixPath

SCOPE = 'source-reviewed-modelcard-preview-not-production'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    require(root.is_dir() and not root.is_symlink(), 'Missing or linked input directory')
    require(not any(path.is_symlink() for path in root.rglob('*')), 'Linked input is forbidden')
    return {path.relative_to(root).as_posix(): digest(path)
            for path in sorted(root.rglob('*')) if path.is_file()}


def load_preview(repo, preview_id, manifest_sha256, baseline):
    require(re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', preview_id), 'Invalid preview ID')
    require(re.fullmatch(r'[a-f0-9]{64}', manifest_sha256), 'Exact manifest SHA256 required')
    parent = repo / 'verification-previews'
    root = parent / preview_id
    require(not parent.is_symlink() and not root.is_symlink(), 'Linked preview owner is forbidden')
    manifest_path = root / 'manifest.json'
    require(manifest_path.is_file() and not manifest_path.is_symlink()
            and digest(manifest_path) == manifest_sha256, 'Reviewed manifest changed')
    manifest = json.loads(manifest_path.read_text())
    require(manifest.get('schema_version') == 1 and manifest.get('scope') == SCOPE
            and manifest.get('preview_id') == preview_id, 'Invalid preview scope/owner')
    require(manifest.get('production_approval') is False
            and manifest.get('daily_deadline_validated') is False, 'Preview is not a production edition')
    cutoff = datetime.fromisoformat(manifest['original_cutoff'])
    require(cutoff.tzinfo is not None and manifest.get('edition_phase') in {
        'global_morning', 'daily_final', 'saturday_daily', 'sunday_weekly'}, 'Invalid original time/phase')
    keys = manifest.get('card_keys')
    require(isinstance(keys, list) and bool(keys) and all(isinstance(k, str) and k for k in keys)
            and len(keys) == len(set(keys)), 'Reviewed card keys must be unique and nonempty')
    require(manifest.get('validation_scope') in {'all_selected', 'reviewed_completed_subset'},
            'Missing precise review coverage')
    require(isinstance(manifest.get('proof_contracts'), list) and manifest['proof_contracts']
            and all(isinstance(v, str) and v for v in manifest['proof_contracts']), 'Missing proof contract identities')
    for field in ('independent_source_review_sha256', 'downstream_verification_sha256'):
        require(isinstance(manifest.get(field), str) and re.fullmatch(r'[a-f0-9]{64}', manifest[field]),
                'Missing exact local validation receipt: ' + field)
    require(manifest.get('baseline_sha256') == baseline, 'Production archive changed since local review')
    payload = root / 'payload'
    actual = inventory(payload)
    require(actual and actual == manifest.get('files_sha256'), 'Preview bytes changed or extra files present')
    require(set(actual) == {'index.html', 'briefing.json', 'briefing.md'}, 'Only reviewed public projections are allowed')
    projection = json.loads((payload / 'briefing.json').read_text())
    require(projection.get('publication', {}).get('visibility') == 'public'
            and projection['publication'].get('full_text_included') is False
            and projection.get('synthetic') is False, 'Only nonsynthetic public projections may be transported')
    require(projection.get('cutoff') == manifest['original_cutoff']
            and projection.get('edition_phase') == manifest['edition_phase'], 'Public projection time/phase changed')
    require([row.get('id') for row in projection.get('issues', [])] == keys, 'Public projected card order/set changed')
    for name in actual:
        path = PurePosixPath(name)
        require(not path.is_absolute() and '..' not in path.parts, 'Invalid payload path')
    return payload, manifest


def compact_notice(manifest):
    """Validate only the reviewed display context, not editorial approval."""
    from zoneinfo import ZoneInfo

    def label(value):
        stamp = datetime.fromisoformat(value)
        require(stamp.tzinfo is not None, 'Display timestamp must be timezone-aware')
        return stamp.astimezone(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M KST')

    cutoff = label(manifest['original_cutoff'])
    if 'display_context' not in manifest:
        return '검증판 · 원문 수집 기준 ' + cutoff + ' · 정기 브리핑과 별도'
    context = manifest['display_context']
    require(isinstance(context, dict) and set(context) == {
        'review_provenance', 'listing_collected_at', 'edition_cutoff',
        'continuous_latest_coverage_claimed'}, 'Invalid display context')
    require(context['edition_cutoff'] == manifest['original_cutoff']
            and context['continuous_latest_coverage_claimed'] is False
            and context['review_provenance'] in {'assisted_editor', 'normal_model_review'},
            'Display context differs from reviewed manifest')
    require(context['listing_collected_at'] is None or (
        isinstance(context['listing_collected_at'], str) and context['listing_collected_at']),
        'Invalid listing timestamp')
    listing = (label(context['listing_collected_at']) if context['listing_collected_at']
               else '별도 수집 기록 참조')
    kind = '편집 보조 검토판' if context['review_provenance'] == 'assisted_editor' else '검증판'
    return ('<aside class="notice" role="note" data-preview-notice="compact">'
            + kind + ' · 목록 수집 ' + listing + ' · 판 기준 ' + cutoff
            + ' · 정기 브리핑과 별도</aside>')


def assemble(repo, output, preview_id='', manifest_sha256=''):
    repo = repo.resolve(strict=True)
    output = output.absolute()
    require(not output.exists() and not output.is_symlink(), 'Output must be fresh')
    require(not output.resolve().is_relative_to(repo), 'Build output must be outside checkout')
    require(bool(preview_id) == bool(manifest_sha256), 'Both preview inputs or neither are required')
    site = repo / 'site'
    baseline = inventory(site)
    require({'index.html', 'archive.json', '.nojekyll'} <= baseline.keys(), 'Normal archive is missing')
    loaded = load_preview(repo, preview_id, manifest_sha256, baseline) if preview_id else None
    shutil.copytree(site, output)
    if loaded:
        payload, manifest = loaded
        route = 'verification/' + preview_id
        destination = output / route
        require(not destination.exists(), 'Preview route collides with normal archive')
        shutil.copytree(payload, destination)
        page = destination / 'index.html'
        content = page.read_text()
        require(content.count('<head>') == 1 and content.count('<body id="top">') == 1,
                'Expected reviewed renderer HTML boundaries are missing')
        cutoff = html.escape(manifest['original_cutoff'])
        scope = '검토 완료 부분집합' if manifest['validation_scope'] == 'reviewed_completed_subset' else '선정 카드 전체 검토'
        note = ('개발 배포 검증판 · ' + scope + ' · 원문 기준 시각 ' + cutoff
                + ' · 정기 운영판·오늘 뉴스·평일 마감 달성을 뜻하지 않습니다.')
        require('display_context' not in manifest or 'data-preview-notice="compact"' in content,
                'Explicit display context requires its exact notice')
        if 'data-preview-notice="compact"' in content:
            require(content.count('data-preview-notice="compact"') == 1
                    and content.count('name="robots" content="noindex,nofollow,noarchive"') == 1
                    and compact_notice(manifest) in content,
                    'Reviewed compact preview notice is missing or stale')
            # The compact renderer already carries the notice; preserve exact reviewed bytes.
        else:
            content = content.replace('<head>', '<head>\n<meta name="robots" content="noindex,nofollow,noarchive">', 1)
            content = content.replace('<body id="top">', '<body id="top"><aside class="notice" role="note">'
                                      + note + '</aside>', 1)
            page.write_text(content)
    require(inventory(site) == baseline, 'Checkout archive changed during assembly')
    built = inventory(output)
    require(all(built.get(name) == value for name, value in baseline.items()), 'Normal public bytes changed')
    extra = set(built) - set(baseline)
    require(extra == ({'verification/' + preview_id + '/' + name for name in loaded[1]['files_sha256']}
                      if loaded else set()), 'Unexpected assembled files')
    return {'scope': 'pages-artifact-transport-only', 'preview_id': preview_id or None,
            'production_file_count': len(baseline), 'production_bytes_unchanged': True,
            'preview_files': sorted(extra), 'public_artifact_sha256': built,
            'production_approval': False, 'daily_deadline_validated': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--preview-id', default='')
    parser.add_argument('--manifest-sha256', default='')
    args = parser.parse_args()
    result = assemble(args.repo, args.output, args.preview_id, args.manifest_sha256)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
