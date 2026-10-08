"""Trava por biometria do próprio aparelho.

O app NUNCA vê, recebe ou guarda rosto, digital ou foto. Ele só pede ao sistema operacional
"confirme que é a dona" e recebe de volta sim ou não. Quem lê o rosto/digital é o aparelho
(Windows Hello, sensor do celular), e esses dados ficam guardados no chip de segurança dele.

- Windows: Windows Hello (rosto, digital ou PIN) pela API UserConsentVerifier.
- Android/iOS (app gerado com `flet build`): extensão oficial flet-local-auth.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

import flet as ft


@dataclass
class Situacao:
    disponivel: bool
    nome: str        # como chamar na tela: "Windows Hello", "biometria do celular"
    motivo: str = ""  # por que não está disponível


async def _windows_situacao() -> Situacao:
    try:
        from winrt.windows.security.credentials.ui import UserConsentVerifier, UserConsentVerifierAvailability as D
    except ImportError:
        return Situacao(False, "Windows Hello", "Pacote do Windows Hello não instalado.")
    try:
        disp = await UserConsentVerifier.check_availability_async()
    except OSError as e:
        return Situacao(False, "Windows Hello", f"O Windows não respondeu ({e}).")
    motivos = {
        D.DEVICE_NOT_PRESENT: "Este computador não tem Windows Hello (câmera, leitor de digital ou PIN do Hello).",
        D.NOT_CONFIGURED_FOR_USER: "Configure o Windows Hello em Configurações > Contas > Opções de entrada.",
        D.DISABLED_BY_POLICY: "O Windows Hello foi desativado pelo administrador deste computador.",
        D.DEVICE_BUSY: "O leitor está ocupado. Tente de novo em instantes.",
    }
    if disp == D.AVAILABLE:
        return Situacao(True, "Windows Hello")
    return Situacao(False, "Windows Hello", motivos.get(disp, "Windows Hello indisponível."))


async def _windows_autenticar(motivo: str) -> bool:
    from winrt.windows.security.credentials.ui import UserConsentVerifier, UserConsentVerificationResult as Res
    return await UserConsentVerifier.request_verification_async(motivo) == Res.VERIFIED


def _servico_local_auth(page: ft.Page):
    """Extensão de biometria do celular (só existe no app gerado com `flet build`)."""
    try:
        import flet_local_auth as fla
    except ImportError:
        return None
    for s in page.services:
        if isinstance(s, fla.LocalAuthentication):
            return s
    servico = fla.LocalAuthentication()
    page.services.append(servico)
    return servico


def _eh_celular(page: ft.Page) -> bool:
    return page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)


async def situacao(page: ft.Page) -> Situacao:
    if _eh_celular(page):
        servico = _servico_local_auth(page)
        if servico is None:
            return Situacao(False, "biometria do celular", "Gere o app com `flet build` para usar a biometria.")
        try:
            if await servico.is_device_supported() and await servico.can_check_biometrics():
                return Situacao(True, "biometria do celular")
            return Situacao(False, "biometria do celular", "Cadastre uma digital ou o rosto nas configurações do celular.")
        except Exception as e:  # noqa: BLE001 - extensão ausente no app de desenvolvimento
            return Situacao(False, "biometria do celular", f"Biometria indisponível ({e}).")
    if sys.platform == "win32":
        return await _windows_situacao()
    return Situacao(False, "biometria", "Este sistema ainda não tem suporte a biometria no app.")


async def autenticar(page: ft.Page, motivo: str = "Confirme que é você para abrir Minhas Finanças") -> bool:
    """True se o aparelho confirmou a dona; False se cancelou ou falhou."""
    if _eh_celular(page):
        servico = _servico_local_auth(page)
        if servico is None:
            return False
        try:
            return await servico.authenticate(motivo, biometric_only=False, persist_across_backgrounding=True)
        except Exception:  # noqa: BLE001 - cancelado, bloqueado etc.
            return False
    if sys.platform == "win32":
        try:
            return await _windows_autenticar(motivo)
        except OSError:
            return False
    return False
