# FUTURE SCORE (Django edition)

「AIより未来を当てられるか？」— 金融・経済分野の未来の出来事について、AIの予測・世論シグナル・あなたの予測を比較し、結果確定後の的中率でランキングする予測プラットフォームのMVPです。

このリポジトリは、もともと Next.js/TypeScript/Prisma で実装した FUTURE SCORE を、**Python（Django 5）で全面的に作り直したもの**です。データモデル・ビジネスルール・画面構成・法務要件はすべて同一で、実装言語とフレームワークのみが異なります。

> **重要（法務・ビジネス上の制約）**
> 本アプリは予測・情報分析を目的としたエンターテインメント/教育サービスです。金銭を賭ける機能、ユーザー間の金銭のやり取り、換金可能なポイント、個別銘柄の売買推奨、投資助言は一切提供しません。「予測スコア」やランキングはアプリ内ゲーミフィケーションであり、金銭的価値を一切持ちません。

## 目次

- [スタック](#スタック)
- [なぜこの構成か](#なぜこの構成か)
- [セットアップ](#セットアップ)
- [環境変数](#環境変数)
- [Docker](#docker)
- [マイグレーション](#マイグレーション)
- [シードデータ](#シードデータ)
- [テスト](#テスト)
- [アーキテクチャ](#アーキテクチャ)
- [セキュリティ](#セキュリティ)
- [画面一覧](#画面一覧)
- [ロードマップ](#ロードマップ)

## スタック

| レイヤー | 技術 |
|---|---|
| Webフレームワーク | Django 5.1 |
| 言語 | Python 3.11 |
| DB | PostgreSQL 16 |
| DBドライバ | psycopg3（`psycopg[binary]`、ネイティブ拡張同梱） |
| フロントエンド | Django テンプレート + 自作CSSデザインシステム（ビルドステップなし） |
| 認証 | Django標準認証（カスタムUserモデル、メールログイン） |
| バリデーション（AI出力） | Pydantic |
| テスト | pytest + pytest-django（ユニット/統合）、Playwright for Python（E2E） |
| 本番サーバー | gunicorn |
| インフラ | Docker / docker-compose |

## なぜこの構成か

- **フロントエンドビルドなし**: Tailwind CDNやnode.js依存を避け、`static/css/app.css` に手書きのユーティリティCSSデザインシステムを実装しています。Django テンプレートがサーバーサイドでHTMLを描画し、投票UIなど一部のインタラクションのみ `static/js/vote.js`（素のJavaScript、fetch API + CSRFトークン処理）で progressive enhancement しています。CDNやビルドツールに一切依存しないため、本番運用がシンプルです。
- **psycopg3**: ネイティブバイナリのダウンロードが必要な旧世代のPythonドライバとは異なり、`psycopg[binary]` はwheelにコンパイル済みのlibpqを同梱しており、追加のシステムパッケージなしで動作します。
- **純粋関数と DB 層の分離**: `scoring/pure.py` はDjango/DBに一切依存しないビジネスロジック（スコア計算・レーティング・ランキング・バッジ判定）です。`pytest`（DBなし）で高速にユニットテストできます。`scoring/services.py` / `scoring/resolution.py` がDBを操作する薄いアダプタ層です。
- **Adapter パターンでAI/世論シグナルを抽象化**: `predictions/providers/ai/` はプロバイダ非依存のインターフェース（`PredictionAIProvider`）+ Mock実装 + OpenAI/Anthropic/Google向けの実装スタブです。`AI_PROVIDER` 環境変数で切り替え、APIキー未設定時は自動的にMockにフォールバックします。世論シグナル（`predictions/providers/opinion/`）、市場データ、経済指標、ニュースも同様のAdapterパターンです。

## セットアップ

### 前提

- Python 3.11+
- PostgreSQL 16（ローカルまたはDocker）

### ローカル実行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env を編集してDB接続情報を設定

# PostgreSQLにデータベースとロールを作成（既に存在する場合は不要）
createdb futurescore
createuser futurescore --pwprompt

python manage.py migrate
python manage.py seed_data      # 開発用デモデータ投入（任意）
python manage.py runserver
```

`http://localhost:8000` にアクセスしてください。

### ログイン情報（`seed_data` 実行後）

| ロール | メールアドレス | パスワード |
|---|---|---|
| 管理者 | admin@futurescore.local | Admin1234! |
| デモユーザー | demo@futurescore.local | Demo1234! |
| 一般ユーザー（22件） | predictor_01@futurescore.local 〜 predictor_22@futurescore.local | Password1! |

## 環境変数

`.env.example` を参照してください。主なもの:

| 変数名 | 説明 | デフォルト |
|---|---|---|
| `DJANGO_DEBUG` | デバッグモード | `True` |
| `DJANGO_SECRET_KEY` | Djangoのシークレットキー（本番では必ず変更） | 開発用の固定値 |
| `ALLOWED_HOSTS` | カンマ区切りの許可ホスト | `localhost,127.0.0.1` |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | PostgreSQL接続情報 | `futurescore` / `futurescore` / `futurescore` / `localhost` / `5432` |
| `AI_PROVIDER` | `MOCK` / `OPENAI` / `ANTHROPIC` / `GOOGLE` | `MOCK` |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_AI_API_KEY` | 各プロバイダのAPIキー（未設定時はMOCKにフォールバック） | 空 |

## Docker

```bash
docker compose up --build
```

`web` サービスが起動時に自動的に `migrate` を実行します。デモデータを投入する場合は別途:

```bash
docker compose exec web python manage.py seed_data
```

## マイグレーション

```bash
python manage.py makemigrations   # モデル変更後
python manage.py migrate
```

`scoring/migrations/0002_seed_badge_catalog.py` は、バッジカタログ（9種類のバッジ定義）を `migrate` 実行時に自動投入するデータマイグレーションです。バッジ付与ロジック（`scoring/services.py: grant_badges`）はバッジコードでカタログを検索するため、このマイグレーションがないと（`seed_data` を実行しない）本番DBでバッジが一切付与されないという実バグがありました — 本リポジトリでは修正済みです。

## シードデータ

```bash
python manage.py seed_data
```

6カテゴリー × 4問 = 24件の予測、管理者1名+デモ1名+一般22名のユーザー、各予測に対するAI予測・世論シグナル、ランダムな投票、締切済み予測の自動確定（スコア・ランキングデータの生成）を行います。何度でも再実行可能です（既存のシードデータを削除してから再作成）。

## テスト

### ユニット・統合テスト（pytest, DBあり）

```bash
python -m pytest tests/ -v
```

- `tests/test_scoring_pure.py` — スコア計算・ストリーク・レーティング・ランキング・バッジ判定のユニットテスト（DB不要、純粋関数のみ）
- `tests/test_ai_mock_provider.py` — Mock AIプロバイダの決定性・出力バリデーションのテスト
- `tests/test_vote_and_resolution.py` — 投票送信・結果確定の統合テスト（実際のPostgreSQLに対して実行、`submit_vote`/`resolve_prediction`の冪等性・監査証跡・バッジ付与を検証）

初回実行時にDjangoが自動でテスト用データベースを作成するため、DBユーザーに `CREATEDB` 権限が必要です:

```sql
ALTER USER futurescore CREATEDB;
```

### E2Eテスト（Playwright）

```bash
python manage.py runserver &
python manage.py migrate && python manage.py seed_data
python -m pytest tests_e2e/ -v
```

実際のブラウザで新規登録→ログイン→投票→ログアウトのフローと、法務ディスクレーマーの表示を検証します。

## アーキテクチャ

```
config/          プロジェクト設定（settings.py, urls.py）
accounts/        カスタムUserモデル、登録・ログイン
core/            通知・監査ログ・分析イベント・サブスクリプション、レート制限、共通エラーハンドリング
predictions/     予測CRUD、投票、AI/世論/市場/経済/ニュースプロバイダ（Adapterパターン）
scoring/         スコア計算・レーティング・ランキング・バッジ（pure.py = DB非依存の純粋ロジック）
adminpanel/      管理画面（KPIダッシュボード、予測CRUD、結果確定、ユーザー管理、監査ログ閲覧）
templates/       Djangoテンプレート
static/          手書きCSSデザインシステム + 投票用バニラJS
tests/           pytest ユニット・統合テスト
tests_e2e/       Playwright E2Eテスト
```

### 主要なビジネスロジック

- **スコア計算**（`scoring/pure.py: calculate_score`）: MVPでは的中+10pt / 不的中0ptの固定ルール。将来的なBrierスコア/対数損失/キャリブレーションボーナスへの差し替えを見越し、関数シグネチャに`confidence`を含めています。
- **レーティング**（`calculate_rating`）: A+/A/B+/B/C+/C/Dの7段階。確定予測件数が一定数（`MIN_RESOLVED_FOR_HIGH_RATING=10`）未満の場合、高レーティング（A+/A/B+）を付与しません（不正防止）。
- **ランキング**（`build_ranking`）: 最低予測回数未満のユーザーを除外した上で、スコア降順→的中率降順→予測件数降順でソート。
- **予測確定**（`scoring/resolution.py: resolve_prediction`）: トランザクション内で全投票をスコアリングし、ユーザー統計・バッジ・通知を更新。同一結果での再実行は安全なno-op、異なる結果での再実行は`ResolutionConflictError`を送出して拒否します（冪等性の保証）。`ScoreEvent`テーブルの`(user, prediction, type)`ユニーク制約が、アプリケーションレベルのチェックに加えたDBレベルの二重防御です。
- **投票**（`predictions/services.py: submit_vote`）: 締切前かつ`OPEN`状態でのみ許可。変更は締切前であれば何度でも可能で、`UserPredictionHistory`に追記専用の監査証跡を残します。

## セキュリティ

- パスワードはDjango標準の`PBKDF2`ハッシュ（bcryptライブラリも依存関係に含む）
- CSRF保護（Djangoミドルウェア標準、`vote.js`はCookieからCSRFトークンを読み取りヘッダーで送信）
- レート制限（`core/middleware.py`）: 登録・ログイン・投票エンドポイントに簡易インメモリのスライディングウィンドウ制限を適用。**複数インスタンス構成ではRedisなど共有ストアへの置き換えが必要**（コード内にコメントで明記）
- セッションCookie: `SameSite=Lax`、本番（`DEBUG=False`）では`Secure`属性を自動付与
- `X-Frame-Options: DENY`
- 管理画面（`/admin-panel/`）は`role=ADMIN`のユーザーのみアクセス可能（`core/decorators.py: admin_required`）
- 生のDjango管理サイト（`/django-admin/`）はスタッフ権限を持つ管理者のみ（データ検証・緊急時のみを想定）

## 画面一覧

| パス | 内容 |
|---|---|
| `/` | ホーム（注目予測・カテゴリー一覧） |
| `/predictions/` | 予測一覧（カテゴリー・ステータスでフィルタ） |
| `/predictions/<slug>/` | 予測詳細（AI予測・ユーザー予測・世論シグナル・投票UI） |
| `/ranking/` | ランキング（総合・カテゴリー別タブ） |
| `/profile/<username>/` | ユーザープロフィール（統計・バッジ・予測履歴） |
| `/me/` | マイページ（自分の統計・月別的中率・累積スコア推移） |
| `/accounts/login/` `/accounts/register/` | ログイン・新規登録 |
| `/admin-panel/` | 管理画面（KPI・予測管理・予測作成・ユーザー管理・AI/世論シグナル閲覧・監査ログ） |
| `/django-admin/` | Django標準管理サイト（生データ検証用、ボーナス機能） |

## ロードマップ（MVP後）

- リアルタイム通知（現状はDB保存のみ、メール/プッシュ配信は未実装）
- Redisベースのレート制限・キャッシュ（マルチインスタンス対応）
- Celery等によるバックグラウンドジョブ（現状は締切超過の予測クローズをリクエスト時に遅延実行）
- 実際のAI/世論/市場データプロバイダへの接続（現状は全てMock実装）
- Brierスコア/対数損失ベースの高度なスコアリング（`scoring/pure.py`の関数シグネチャは既に対応済み）
- Stripe等による`Subscription`モデルの実課金化（現状はモデルのみ存在し、課金ロジックは未実装）
- 金融以外のカテゴリー（政治・スポーツ・テクノロジー等）の解放（`Category`enumに予約済み）
