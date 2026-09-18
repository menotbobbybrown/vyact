<div align="center" markdown="1">
  <img src="assets/icon-transparent/icon_512x512.png" alt="Vyact 로고" width="120" />

# Vyact

[English](README.md) · [한국어](README_KO.md) · [简体中文](README_ZH.md) · [日本語](README_JA.md) · [ไทย](README_TH.md) · [Tiếng Việt](README_VI.md)

### 로컬 AI를, 실제로 쓰는 도구로.

Vyact는 로컬 AI를 일상적인 작업에 연결합니다. 내 파일에 대해 질문하고, 메일에 답장하고, 코드를 작성하고, 크롬에서 읽고 쓰며 언어를 배우세요. 선택한 모델과 데스크톱 워크스페이스가 이 모든 작업을 이어줍니다.

**Apple Silicon Mac · Windows · Linux x64**

오픈소스입니다. 내 컴퓨터에서 모델을 실행하거나 외부 AI 제공자를 선택할 수 있습니다.

[**Vyact 다운로드**](https://github.com/vyact/vyact/releases/latest) · [**활용 데모 보기**](https://youtu.be/V3NTHU94lP8)

[![라이선스: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-7c3aed.svg?style=flat-square)](LICENSE)
[![Chrome 확장](https://img.shields.io/badge/browser-Chrome%20Extension-4285f4.svg?style=flat-square)](https://chromewebstore.google.com/detail/vyact/opfbakfhoojmdkbbhcglolkpgmenjbib)
[![최신 버전](https://img.shields.io/github/v/release/vyact/vyact?style=flat-square&label=release)](https://github.com/vyact/vyact/releases/latest)

[시작하기](#문서-하나로-시작하세요) · [활용 예시](#일상적인-작업을-하나의-워크스페이스에서) · [데스크톱](#나만의-데스크톱-워크스페이스) · [크롬 확장](#채팅-사이드바를-넘어-vyact-for-chrome) · [후원](#vyact-후원하기) · [기여 안내](CONTRIBUTING.md)
</div>

---

[![모델 성능 테스트·문서 질문·메일 답장·브라우저 교정 통합 데모](assets/readme/demo-complete-showcase.png)](https://youtu.be/V3NTHU94lP8)

3분 29초 데모에서 모델 선택과 성능 테스트, 문서 질의응답과 원문 근거 확인, 이메일 서명과 AI 답장 작성, 브라우저 글쓰기 교정을 살펴보세요. 가상의 자료를 사용한 실제 앱 녹화이며, 대기 구간을 편집했고 문서 답변 생성 일부는 2배속입니다. MLX는 Apple Silicon Mac에서 사용할 수 있으며, 성능 테스트 결과는 하드웨어·모델·설정에 따라 달라집니다.

## 일상적인 작업을 하나의 워크스페이스에서

### 답을 찾고, 원문에서 확인하세요

대화에 PDF를 첨부하고 주요 결정, 남은 질문, 다음 할 일처럼 필요한 내용을 물어보세요. 답변의 출처를 열어 원문과 비교할 수 있습니다. 자주 쓰는 문서는 색인해 두면 매번 다시 첨부하지 않고 질문할 수 있습니다.

**이렇게 물어보세요:** “이 문서의 주요 위험 요소 3개와 근거가 되는 원문을 알려줘.”

### 읽은 메일을 바로 답장으로 이어가세요

대화 옆에서 Gmail이나 Outlook 메일을 읽고, 관련 파일을 연결해 AI에게 답장 작성을 요청하세요. 생성된 초안을 미리 확인하고 메일 편집기에 넣은 뒤, 최종 내용을 다듬어 전송할 수 있습니다.

**이렇게 물어보세요:** “다음 할 일을 확인하고 마감일을 묻는 짧은 답장을 작성해 줘.”

Google·Microsoft 연결은 선택 사항이며 OAuth 앱 설정이 필요합니다. 계정을 연결하기 전에 로컬 문서로 먼저 Vyact를 체험할 수 있습니다.

### 페이지를 떠나지 않고 글을 다듬으세요

게시물, 메일, 댓글을 쓰면서 맞춤법과 문법을 확인하세요. 밑줄 표시를 눌러 변경 내용을 미리 보고 **적용**하거나 **무시**할 수 있습니다. 글 전체를 다듬을 때도 원문과 결과를 비교한 뒤 사용할 수 있습니다.

<p align="center">
  <img src="assets/readme_ko/feature-01-live-writing-ko-1280x720.png" alt="입력 중 문법 오류를 확인하고 원하는 수정만 적용하는 Vyact 글쓰기 도우미" width="100%" />
</p>

**크롬 확장 설치와 Vyact 데스크톱 앱 실행이 필요합니다.** 지원되는 웹 편집기에서 원하는 수정만 선택할 수 있으며, 적용하기 전에는 원문이 바뀌지 않습니다.

## 문서 하나로 시작하세요

1. [Vyact를 다운로드](https://github.com/vyact/vyact/releases/latest)하고 설치한 뒤 실행하세요.
2. 로컬 모델을 사용하려면 **Vyact**를 선택하세요. 메모리 예상량과 색상 안내를 참고해 모델을 고르고 다운로드한 뒤 준비가 끝날 때까지 기다리세요. 이미 사용하는 AI 제공자를 선택할 수도 있습니다.
3. 대화에 PDF를 첨부하고 **“핵심 내용 3개와 근거가 되는 원문을 알려줘”**라고 질문하세요.
4. 답변의 출처를 열어 원문과 비교하세요.

첫 다운로드와 실행 준비에는 시간과 인터넷 연결이 필요합니다. 답변 속도는 하드웨어와 모델에 따라 달라집니다. 이 첫 작업에는 메일 계정 연결이나 크롬 확장이 필요하지 않습니다.

[설치 요구 사항과 운영체제별 안내](#설치와-연결)

## 나만의 데스크톱 워크스페이스

문서, 대화, 도구를 한곳에 모으세요. 하나의 작업으로 시작하고 필요한 연결과 기능을 더할 수 있습니다.

| 기능 | 활용 방법 |
| --- | --- |
| AI 대화와 이력 | 로컬·외부 모델과 대화하고 파일·지원 이미지 첨부, 즐겨찾기, 요약, 대화 내보내기 사용 |
| 문서 검색과 지식 컬렉션 | 문서·메모·색인한 이메일을 묶고 검색 범위·지침을 지정해 질문, 원문 근거 확인 |
| 프로젝트와 기억 | 프로젝트별 작업 지침·폴더·대화를 관리하고 요약·결정·할 일을 확인·편집 |
| 메모와 빠른 할 일 | 표·목록·이미지·코드를 포함한 메모 작성, RAG 검색, 간단한 할 일 완료 상태 관리 |
| 메일·파일·일정 | Gmail·Outlook, Drive·OneDrive, Google·Microsoft 일정 연동, AI 초안·서명·정형 문구·수신자 그룹 활용 |
| Google 문서 도구 | 권한이 있는 Docs·Sheets·Slides·Forms를 대화에서 조회·작성·수정하고 설문 응답 확인 |
| 코드 작업과 리뷰 | 연결한 폴더의 파일 검색·생성·편집, 프로젝트 검사, Git 변경 확인, 추적한 수정 되돌리기 |
| 브라우저 작업 | AI에 웹 검색·페이지 읽기·클릭·입력을 요청하고, 로그인 등 직접 해야 할 단계 후 작업 계속 |
| 음성과 회화 연습 | 음성 대화·답변 읽어주기, 대본 생성·저장·역할 선택, 상대역 듣기와 내 대사 연습 |
| 개인화·프롬프트 | 답변 스타일 선택, 대화 분석으로 만든 프로필을 검토 후 적용, 시스템 프롬프트와 스킬 관리 |
| 모델 선택과 성능 비교 | GGUF·MLX 검색·다운로드, 메모리 예상량·저장 위치 관리, 내 하드웨어에서 설정별 속도 비교 |
| MCP·로컬 API | 로컬·원격 도구 연결, 요청별 도구 선택·실행 승인, 활성 모델을 다른 앱에서 API로 사용 |
| 백업과 앱 설정 | 로컬·Drive·OneDrive 백업·복원, 계정 전환·알림·단축키·테마, 8개 언어 UI |

Google·Microsoft 연동에는 계정 설정과 권한이 필요하며, 두 서비스에서 제공하는 대화형 도구의 범위는 동일하지 않습니다.

## 채팅 사이드바를 넘어: Vyact for Chrome

지금 읽거나 작성 중인 페이지에서 AI를 사용하세요. **크롬 확장을 설치하고 Vyact 데스크톱 앱을 실행**하면 선택한 모델에 연결됩니다.

| 기능 | 활용 방법 |
| --- | --- |
| 페이지 옆 AI 대화 | 현재 페이지·선택 텍스트·파일을 대화에 연결하고 요약·후속 질문, 대화 이력·프롬프트 사용 |
| 웹페이지 지식 저장 | 읽은 페이지를 Vyact에 색인·저장해 나중에 검색·질문에 활용 |
| 번역과 읽기 모드 | 선택 글 빠른 번역·상세 번역, 본문 또는 선택 영역의 문단별 번역, 읽어주기 |
| 글쓰기 검사·다듬기 | 오류 밑줄, 개별·일괄 적용·무시·되돌리기, 문체·출력 언어·추가 지시를 반영한 전후 비교 |
| 글쓰기 설정 | 자동 검사는 검사 설정에서 모든 사이트에 공통으로 켜고 끄며, 사이트별 사용 중지는 도구 모음의 전원 버튼으로 별도 설정. 단어 제안과 수정 이유는 기본적으로 꺼져 있으며 선택적으로 활성화 |
| 단어장·문장 보관함 | 뜻·발음·예문 확인, 단어와 번역 문장을 출처와 함께 저장·검색·듣기·삭제 |
| Netflix 자막 학습 | 이중 자막, 문장 이동·반복·자동 일시정지, 전체 스크립트 탐색 |
| 약점에 맞춘 표현 설명 | 언어별 숙어·연결음·문법·뉘앙스 등 학습 초점 선택, 자막·표현 질문과 문장 저장 |
| AI 작품 찾기 | 기억나는 줄거리나 보고 싶은 내용을 설명해 작품 후보를 받고 Netflix 검색으로 이동 |
| 데스크톱 AI의 브라우저 연결 | Vyact의 브라우저 작업을 Chrome에서 실행하고 페이지의 동작 확인 |

크롬 확장은 실행 중인 Vyact 데스크톱 앱과 함께 사용합니다. 글쓰기 기능은 지원되는 웹 편집기에서 동작하며, Netflix 학습은 작품에서 제공하고 불러온 자막 트랙에 따라 달라집니다. AI 작품 후보가 해당 지역의 실제 제공 목록을 보장하지는 않습니다.

[**크롬 확장 설치**](https://chromewebstore.google.com/detail/vyact/opfbakfhoojmdkbbhcglolkpgmenjbib)

## 더 자세히 살펴보기

### 다시 찾을 수 있는 메모

계획과 결정을 서식 있는 메모로 남기고, 나중에 지식 검색으로 다시 질문하세요.

<p align="center">
  <img src="assets/readme/feature-memo.png" alt="Vyact의 서식 있는 메모 워크스페이스" width="100%" />
</p>

### 소리 내어 대화 연습

자유롭게 대화하거나 저장한 연습 대본에서 역할을 선택하세요. 자동 읽어주기와 재생 속도 조절을 활용해 답변을 듣고 연습할 수 있습니다.

<p align="center">
  <img src="assets/readme/feature-voice-chat.png" alt="Vyact 음성 대화와 말하기 연습" width="100%" />
</p>

### 읽고 있는 내용을 이해하세요

사이드 패널에서 기사를 요약하고, 페이지를 떠나지 않은 채 낯선 단어의 발음과 예문을 확인하세요.

<p align="center">
  <img src="assets/readme/feature-plugin.png" alt="웹 기사 요약과 단어의 발음·예문을 함께 확인하는 Vyact" width="100%" />
</p>

## 내 컴퓨터에 맞는 로컬 모델 선택

다운로드 전에 모델 크기와 메모리 예상량을 내 컴퓨터와 비교하세요. 실제 메모리 사용량은 모델과 설정에 따라 달라집니다. Vyact가 GGUF 또는 Apple Silicon용 MLX 모델에 맞는 런타임을 준비합니다. 공개 모델은 API 키 없이 사용할 수 있으며, 접근이 제한된 Hugging Face 모델에는 권한이 있는 계정이 필요합니다.

<p align="center">
  <img src="assets/readme_ko/feature-model-ko-1280x720.png" alt="컴퓨터 메모리와 모델의 예상 사용량을 비교하는 로컬 모델 검색 화면" width="100%" />
</p>

<details>
<summary>내 하드웨어에서 모델 설정 비교하기</summary>

**모델 설정 > 성능 테스트**에서 짧은 입력, 긴 입력, 후속 대화로 지원되는 설정을 비교하세요. 응답 시간, 생성 속도, 토큰 수를 확인한 뒤 **이 설정 사용**과 **적용**으로 설정을 활성화할 수 있습니다.

결과는 답변 품질이 아닌 속도를 비교합니다. 중단해도 완료된 측정은 유지됩니다. 테스트 후 이전 모델과 설정을 복원하며, 복원 중 오류가 발생하면 알립니다. 새 테스트를 시작하면 해당 모델의 이전 결과를 대체합니다.

<p align="center">
  <img src="assets/readme/feature-model-benchmark.png" alt="응답 시간과 토큰 수를 보여주는 모델 성능 테스트 결과" width="100%" />
</p>

</details>

## 설치와 연결

<details>
<summary>설치 요구 사항과 운영체제별 안내</summary>

### 데스크톱 앱 설치

[GitHub Releases](https://github.com/vyact/vyact/releases)에서 **Apple Silicon Mac(M1 이상)**, **Windows**, **Linux x64**용 Vyact를 다운로드하고 설치한 뒤 실행하세요. macOS는 DMG, Windows는 EXE 설치 파일, Linux는 AppImage와 DEB 패키지로 제공합니다. Intel Mac은 현재 지원하지 않습니다.

#### Linux에서 실행

AppImage는 설치 없이 실행할 수 있습니다. 다운로드한 폴더에서 다음 명령을 실행하세요.

```bash
chmod +x Vyact-*.AppImage
./Vyact-*.AppImage
```

Ubuntu, Debian 또는 호환 배포판에서는 DEB 패키지를 설치할 수 있습니다.

```bash
sudo apt install ./vyact_*_amd64.deb
```

DEB 설치 후 애플리케이션 메뉴에서 **Vyact**를 실행하세요.

### 처음 실행하기 전에

Vyact는 Python을 포함하며, 앱에서 지정한 버전의 모델 런타임을 전용 폴더에 준비합니다. macOS와 Windows에서는 필요한 런타임을 자동으로 다운로드하며, Linux 패키지에는 CPU 런타임이 포함되어 있습니다. 기존 사용자는 Vyact 관리 런타임으로 전환하기 전에 안내를 받으며, 런타임 버전 변경에는 확인이 필요합니다. 기존 시스템 설치는 그대로 유지합니다.

| 운영체제 | 기본 앱 실행 요구 사항 | 기능별 요구 사항 |
| --- | --- | --- |
| macOS (Apple Silicon) | 없음 | **로컬 GGUF 모델**<br>• 지정된 런타임을 자동으로 다운로드하고 관리<br><br>**로컬 MLX 모델**<br>• 전용 환경에 oMLX 설치, macOS 15 이상과 Git 필요<br><br>**Elasticsearch**<br>• 네이티브 모드는 외부 의존성 없음, 컨테이너 모드는 Docker Desktop 선택 사용<br><br>**Kokoro TTS**<br>• `espeak-ng`를 설치해야 할 때만 Homebrew 필요 |
| Windows | 없음 | **로컬 GGUF 모델**<br>• 지정된 런타임을 자동으로 다운로드하고 관리<br><br>**Elasticsearch**<br>• 네이티브 모드는 외부 의존성 없음, 컨테이너 모드는 Docker Desktop 선택 사용<br><br>**Kokoro TTS**<br>• `espeak-ng`를 설치해야 할 때만 `winget` 필요 |
| Linux (x64) | glibc 2.35 이상의 x86-64 데스크톱 환경. DEB 패키지는 선언된 데스크톱 라이브러리 의존성을 APT로 설치 | **로컬 GGUF 모델**<br>• CPU 런타임 포함<br><br>**Elasticsearch**<br>• 네이티브 모드는 외부 의존성 없음, 컨테이너 모드는 Docker 선택 사용<br><br>**브라우저·Kokoro TTS 의존성**<br>• 시스템 라이브러리 또는 `espeak-ng`가 없으면 지원 패키지 관리자(`apt-get`, `dnf`, `zypper`, `pacman`)와 데스크톱 PolicyKit 인증 에이전트 필요. `pkexec`로 권한을 요청하며, 없으면 비밀번호 없이 실행 가능하거나 인증이 캐시된 `sudo`만 시도 |

Docker는 선택 사항입니다. Vyact가 지식 검색용 네이티브 Elasticsearch 배포판을 다운로드하고 실행할 수 있습니다. 패키지 관리자는 선택한 기능에 필요한 시스템 구성 요소가 없을 때만 필요합니다.

### 사용자 지정 LLM 제공자 연결

OpenAI 호환 `/chat/completions` API를 제공하는 서버에 연결할 수 있습니다. 초기 설정에서 **Custom LLM**을 선택하거나, 설치 후 사이드바의 제공자 관리에서 연결을 추가·수정하세요.

- **연결 이름** — Vyact에 표시할 이름입니다.
- **Base URL** — `/chat/completions`를 제외한 API 기본 주소입니다. 예: `http://localhost:11434/v1`
- **API 키** — 로컬 서버에서는 선택 사항이며, Bearer 인증을 사용하는 서버에서는 필요합니다.
- **모델 ID** — API가 요구하는 정확한 모델 식별자입니다.
- **추가 헤더** — 게이트웨이나 조직별 인증에 필요한 헤더를 선택적으로 지정합니다.

기존 OpenAI 호환 로컬 서버의 연결 예시입니다.

```text
연결 이름: Local LLM
Base URL: http://localhost:8080/v1
API 키: (비워 두기)
모델 ID: my-local-model
추가 헤더: (없음)
```

사용자 지정 연결 설정은 Vyact 백업·복원에 포함됩니다. 스트리밍, 도구 호출, 이미지 입력은 연결한 서버와 모델의 기능 및 OpenAI API 호환성에 따라 달라집니다.

### 크롬 확장 사용

1. [크롬 웹스토어에서 Vyact](https://chromewebstore.google.com/detail/vyact/opfbakfhoojmdkbbhcglolkpgmenjbib)를 설치하세요.
2. Vyact 데스크톱 앱을 실행하세요.
3. 크롬 도구 모음에 Vyact를 고정하고 일반 웹페이지에서 사이드 패널을 여세요.

</details>

<details>
<summary>계정, 도구, 다른 앱 연결하기</summary>

- **Google:** **설정 > Google**에서 OAuth 자격증명 JSON을 업로드하고 설정 가이드에 따라 계정을 연결하고 사용할 서비스의 권한을 허용하세요.
- **Microsoft:** **설정 > Microsoft**에서 Microsoft Entra 앱의 Client ID를 입력하고 설정 가이드를 따르세요. 회사·학교 계정은 관리자 승인이 필요할 수 있습니다.
- **MCP와 스킬:** **설정 > AI 도구**에서 도구를 추가하고 **설정 > 스킬**에서 재사용할 지침을 관리하세요.
- **다른 앱:** **설정 > API 서버**에서 로컬 모델의 엔드포인트, 모델 ID 또는 OpenClaw 설정을 복사하세요. 필요하면 토큰 인증을 활성화하세요.

</details>

### 내 데이터와 AI 제공자 선택

Vyact가 관리하는 로컬 모델로 AI 대화의 맥락을 내 컴퓨터에서 처리하거나, OpenAI·Gemini·Claude 또는 사용자 지정 OpenAI 호환 서버에 연결할 수 있습니다. 외부 AI 제공자를 사용하면 요청에 필요한 맥락이 해당 제공자로 전송됩니다. 연결한 메일·클라우드 파일 기능은 각 서비스와 통신합니다.

백업에 포함할 항목을 선택하고 로컬, Google Drive 또는 OneDrive에 저장할 수 있습니다. 내보낸 백업에는 OAuth 토큰이 포함되지 않습니다.

## Vyact 후원하기

Vyact는 독립적으로 개발하는 오픈소스 프로젝트입니다. 작업에 도움이 되었다면 개발, 테스트, 모델 호환성 개선을 후원할 수 있습니다. 필요한 사람에게 Vyact를 소개하는 것도 큰 도움이 됩니다.

<div align="center" markdown="1">

[![Support on Ko-fi](https://img.shields.io/badge/Support%20on-Ko--fi-ff5e5b?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/vyact)
[![Support with PayPal](https://img.shields.io/badge/Support%20with-PayPal-00457c?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/vyact)
[![Support on Patreon](https://img.shields.io/badge/Support%20on-Patreon-f96854?style=for-the-badge&logo=patreon&logoColor=white)](https://www.patreon.com/cw/vyact)

**Vyact가 독립적인 오픈소스 프로젝트로 꾸준히 발전할 수 있도록 함께해 주셔서 감사합니다.**
</div>

## 기여와 피드백

코드, 문서, 번역, 테스트, 아이디어, 버그 제보와 사용 의견을 환영합니다. 참여하기 전에 [기여 안내](CONTRIBUTING.md)를 읽어 주세요.

프로젝트 역할과 의사결정 방식은 [거버넌스](GOVERNANCE.md)를 참고하세요.

질문이나 설치 도움이 필요하면 제목 앞에 `[Question]`을 붙여 이슈를 등록해 주세요.

보안 취약점은 공개 이슈 대신 [보안 정책](SECURITY.md)에 따라 제보해 주세요.

## 라이선스

Vyact는 [GNU Affero General Public License v3.0](LICENSE)(AGPL-3.0)으로 배포됩니다.

Vyact를 수정하고 웹 앱이나 SaaS처럼 네트워크를 통해 수정 버전을 제공하는 경우, 해당 소스 코드를 동일한 라이선스로 공개해야 합니다.

## 브랜드와 상표

Vyact 이름, 로고, 공식 시각 브랜드 자산에는 AGPL-3.0 라이선스가 적용되지 않습니다. 공식 프로젝트를 정확하게 지칭할 수 있지만, 포크와 수정 버전은 명확히 구분되는 이름과 시각적 정체성을 사용해야 합니다. [Vyact 브랜드 및 상표 정책](TRADEMARKS.md)을 확인하세요.
