<p align="center">
  <img src="server/static/logo-default.png" alt="Logo Snipe Bridge" width="560">
</p>

<h1 align="center">Snipe Bridge</h1>

<p align="center">Bezpieczny pomost między Snipe-IT a starszymi, ręcznymi terminalami kodów kreskowych.</p>

<p align="center"><a href="README.md">English</a> · <a href="docs/installation.md">Instalacja</a> · <a href="docs/user-guide-pl.md">Instrukcja użytkownika</a> · <a href="docs/troubleshooting.md">Rozwiązywanie problemów</a></p>

Snipe Bridge pozwala używać terminali z Windows CE / Windows Mobile do wydań i zwrotów sprzętu w Snipe-IT. Token API pozostaje wyłącznie na serwerze, a terminal otrzymuje prosty interfejs dopasowany do ekranu o szerokości 320 px.

![Panel operatora Snipe Bridge](docs/images/operator.png)

## Najważniejsze możliwości

- parowanie jednorazowym kodem QR albo sześciocyfrowym kodem ręcznym;
- pojedyncze i masowe wydania oraz zwroty;
- wyszukiwanie przez Asset Tag, numer seryjny, pole dodatkowe oraz QR z adresem `/hardware/<ID>`;
- logowanie OpenID Connect i awaryjne konto lokalnego administratora;
- historia operacji użytkownika, pełny widok administratora i eksport CSV/XLSX;
- konfiguracja połączenia Snipe-IT, statusów, logo, kolorów i języka w panelu administratora;
- interfejs polski i angielski;
- kontener Docker, pliki Compose i przykład stosu Portainera;
- trwała baza SQLite, rotacyjne kopie zapasowe i endpointy diagnostyczne.

## Szybki start

```bash
cp .env.example .env
# Ustaw SECRET_KEY, ADMIN_PASSWORD, SNIPEIT_BASE_URL i SNIPEIT_API_TOKEN.
docker compose up -d --build
```

Panel operatora: `http://SERWER:8080/`  
Terminal: `http://SERWER:8080/terminal`

Na środowisku produkcyjnym użyj reverse proxy z HTTPS, ustaw `SESSION_COOKIE_SECURE=true` i wykonuj kopie trwałego wolumenu `/data`.

## Dokumentacja

- [Instrukcja użytkownika po polsku](docs/user-guide-pl.md)
- [Pełny indeks dokumentacji](docs/README.md)
- [Instalacja Docker, Compose i Portainer](docs/installation.md)
- [Zmienne środowiskowe](docs/configuration.md)
- [Logowanie OIDC](docs/authentication.md)
- [Administracja i utrzymanie](docs/administration.md)
- [Rozwiązywanie problemów](docs/troubleshooting.md)

## Licencja

Projekt jest udostępniany na licencji [MIT](LICENSE).
