# Changelog

## 1.0.0-rc14

- translate terminal batch quantities with correct English singular and plural forms (`1 ITEM`, `2 ITEMS`);
- fix translation immediately after protected HTML tags, including Snipe-IT status selectors;
- complete missing terminal, pairing, operator, Snipe-IT error, and activity-history translations;
- localize CSV/XLSX audit exports, headers, messages, sheet names, and download filenames to the operator language;
- add a whole-template translation audit and rendered batch-terminal regression coverage.

## 1.0.0-rc13

- stop terminal activity heartbeats from modifying the screen-state `updated_at` value;
- prevent polling from treating ordinary scanner keystrokes as an external mode change and reloading the page during a scan;
- retain `last_activity_at` updates for idle-session expiry without invalidating the current terminal document;
- extend the end-to-end QR test through the redirected asset-confirmation screen;
- add a regression test proving that `/terminal/touch` leaves the terminal status signature unchanged.

## 1.0.0-rc12

- remove the global hardware-action handler from the printable `keypress` event;
- prevent lowercase `r` (character code 114) from being mistaken for the MC31xx green key and submitting a URL immediately before that character;
- prevent lowercase `s` (character code 115) from being mistaken for the MC31xx red key;
- retain green/red terminal handling on `keydown`, where virtual-key codes do not collide with printable lowercase characters;
- add a regression check covering the exact `r`/`s` collision found in scanned Snipe-IT URLs.

## 1.0.0-rc11

- canonicalize a scanned Snipe-IT URL in the terminal before form submission;
- send only the short `/hardware/<ID>` path through legacy IE Mobile instead of the complete URL;
- apply the same shortening to Enter-based, hardware-key, and manually clicked submissions;
- add a regression check for client-side hardware QR canonicalization.

## 1.0.0-rc10

- stop the terminal from submitting a scan after a pause between ordinary barcode characters;
- begin automatic submission only after the scanner's Enter key and then wait for the complete value to remain stable;
- retain manual submission through the visible pairing and scan buttons;
- add a regression check preventing character-by-character input from starting the submit timer.

## 1.0.0-rc9

- force terminal mode changes to navigate to a unique cache-busted document URL and disable caching of terminal HTML;
- recognize a numeric asset ID from any scanned `/hardware/<ID>` segment, regardless of domain, surrounding text, suffixes, or whitespace inserted by a legacy scanner;
- make the displayed build version part of the application code instead of allowing a stack variable to label an older cached image as a newer release;
- add an end-to-end terminal POST test proving that a foreign-host hardware URL reaches the direct Snipe-IT `/hardware/<ID>` API endpoint.

## 1.0.0-rc8

- wait until legacy scanner input has stopped changing before accepting its Enter key and submitting a scan;
- recognize Snipe-IT asset QR codes by any URL path ending in `/hardware/<numeric ID>`, independently of the installation hostname and protocol;
- tolerate query strings, fragments, wrapping quotes, Unicode framing characters, and decoded URL paths in asset QR values;
- replace asset lookup errors containing raw scanned URLs with a concise localized message;
- add regression tests for complete scanner input and portable Snipe-IT QR URL variants.

## 1.0.0-rc7

- move the unpaired-terminal PL/EN selector into the upper-right corner of the terminal header;
- render a dedicated fixed-width 320 px guard when the operator panel is opened from a Windows CE or MC31xx terminal;
- omit the underlying operator and sign-in interface entirely for server-detected legacy terminals;
- show only the sign-in description field matching the current administrator-interface language while preserving the other translation;
- replace mixed-language description labels with complete Polish and English wording;
- add regression tests for the terminal header selector, legacy operator guard, hidden sign-in fields, and language-specific description controls.

## 1.0.0-rc6

- retain the language selected on the sign-in page for the signed-in operator and propagate it to the paired terminal;
- add Polish/English selectors to the sign-in and unpaired-terminal screens;
- complete terminal, QR-pairing, dynamic error, activity-history, and Snipe-IT response translations;
- add regression checks for translation round trips and reported bilingual terminal phrases;
- preserve exact Snipe-IT status names while displaying localized administrator controls;
- support editable or disabled sign-in descriptions and an optional identity-provider configuration notice;
- refresh status labels from Snipe-IT with a four-second success, warning, or error popup;
- accept complete long barcode/QR values and wait for legacy scanner input to settle before submission;
- show reciprocal screen guards when an operator page is opened on a legacy terminal or a terminal page is opened on a large screen.

## 1.0.0-rc5

- replace Google-only authentication with configurable OpenID Connect while retaining legacy environment-variable compatibility;
- support optional e-mail-domain restrictions, configurable claims, administrator groups, and provider-aware audit entries;
- mask and preserve the OIDC client secret instead of returning it in settings HTML;
- populate checkout, ready, and service selectors from Snipe-IT status labels;
- show and copy the correct OIDC callback URL in the administrator panel;
- complete activity-history translations for checkout and return mode changes;
- block dragging and the image context menu on the displayed application logo.

## 1.0.0-rc4

- keep the scan field focused and restore focus after non-field interaction;
- recognize MC31xx green/red keys as both phone keys and F14/F15 mappings;
- strengthen terminal and operator polling after mode and terminal changes;
- preserve `Asset Tag` and `UAM Asset Tag` as untranslated Snipe-IT field names;
- prevent partial-word localization such as `listay`;
- remove the scan-type hint row below terminal scan fields;
- add regression coverage for the core 0.8.4 pairing and mode-change flow.

## 1.0.0-rc3

- display successful and informational prompts as four-second popups while keeping errors persistent;
- synchronize saved settings across all Gunicorn workers on every request;
- never return the configured Snipe-IT API token in settings HTML and add explicit token removal;
- use `Snipe Bridge` and `#FFCD05` as the generic application and primary-color defaults;
- replace the configurable accent with a fixed green success color;
- apply the selected primary color consistently to controls and their borders;
- add the supplied barcode-and-hedgehog logo and matching favicon;
- expand localization of historical operation messages while protecting user and asset data.

## 1.0.0-rc2

- completed bidirectional Polish and English localization for the operator panel, terminal, settings, audit view, and server messages;
- prevented partial phrase replacement that produced mixed-language sentences;
- fixed the local administrator audit message to describe username/password authentication;
- changed generic Snipe-IT defaults to `Deployed`, `Ready to Deploy`, and `Pending`;
- removed the organization-specific default custom field and clean up that exact rc1 value on startup;
- replaced the remaining organization-specific favicon with generic SVG placeholders;
- fixed spacing and alignment in the administrator settings view;
- added accessible information popups explaining every configurable color;
- set `/data/bridge.db` and `/data/branding/logo` as image defaults.

## 1.0.0-rc1

- first generic release based on the 0.8.4 proof of concept;
- introduced administrator-managed branding and Snipe-IT settings;
- added Docker Compose, Portainer, GitHub Actions, and open-source project files.
