"""Changement du peripherique de sortie audio par defaut (Windows), pour
l'action 'audio_output' (ex: basculer casque/enceintes depuis un bouton).

Windows n'expose aucune API publique pour changer le peripherique par
defaut - Microsoft l'a volontairement laisse hors de l'API publique. Le
seul moyen (utilise par les Parametres son de Windows eux-memes en
interne, et par tous les outils tiers comme EarTrumpet/SoundSwitch) est
l'interface COM non documentee mais stable depuis Windows Vista
IPolicyConfig::SetDefaultEndpoint. L'enumeration des peripheriques passe
par pycaw (wrapper mature autour de l'API Core Audio documentee).
"""

from __future__ import annotations

from .actions import SYSTEM

_CLSID_POLICY_CONFIG = "{870af99c-171d-4f9e-af0d-e63df40c2bc9}"
_IID_POLICY_CONFIG = "{f8679f50-850a-41cf-9c72-430f290290c8}"

# eConsole, eMultimedia, eCommunications - on bascule les 3 roles pour que
# le peripherique devienne a la fois le defaut "normal" et le defaut
# "communications", comme cliquer sur "Definir par defaut" dans les
# parametres son de Windows.
_ROLES = (0, 1, 2)


def list_playback_devices() -> list[dict]:
    """[{id, name}] pour chaque peripherique de sortie audio actif,
    pour le picker recherchable de la popup d'emplacement."""
    if SYSTEM != "Windows":
        raise RuntimeError("Le changement de sortie audio n'est disponible que sur Windows")

    import pythoncom
    from pycaw.constants import DEVICE_STATE, EDataFlow
    from pycaw.utils import AudioUtilities

    pythoncom.CoInitialize()
    try:
        devices = AudioUtilities.GetAllDevices(
            data_flow=EDataFlow.eRender.value,
            device_state=DEVICE_STATE.ACTIVE.value,
        )
        return [{"id": d.id, "name": d.FriendlyName} for d in devices]
    finally:
        pythoncom.CoUninitialize()


def set_default_playback_device(device_id: str) -> None:
    """Bascule le peripherique de sortie par defaut vers `device_id`
    (identifiant opaque retourne par list_playback_devices, a choisir dans
    le picker - pas destine a etre tape a la main)."""
    if SYSTEM != "Windows":
        raise RuntimeError("Le changement de sortie audio n'est disponible que sur Windows")
    if not device_id:
        raise ValueError("Aucun peripherique audio choisi")

    import pythoncom
    import comtypes
    from comtypes import COMMETHOD, GUID, HRESULT
    from ctypes import c_int, c_void_p, c_wchar_p

    class IPolicyConfig(comtypes.IUnknown):
        _iid_ = GUID(_IID_POLICY_CONFIG)
        _methods_ = [
            COMMETHOD([], HRESULT, "GetMixFormat",
                      (['in'], c_wchar_p, "pszDeviceName"), (['out'], c_void_p, "ppFormat")),
            COMMETHOD([], HRESULT, "GetDeviceFormat",
                      (['in'], c_wchar_p, "pszDeviceName"), (['in'], c_int, "bDefault"),
                      (['out'], c_void_p, "ppFormat")),
            COMMETHOD([], HRESULT, "ResetDeviceFormat", (['in'], c_wchar_p, "pszDeviceName")),
            COMMETHOD([], HRESULT, "SetDeviceFormat",
                      (['in'], c_wchar_p, "pszDeviceName"), (['in'], c_void_p, "pEndpointFormat"),
                      (['in'], c_void_p, "pMixFormat")),
            COMMETHOD([], HRESULT, "GetProcessingPeriod",
                      (['in'], c_wchar_p, "pszDeviceName"), (['in'], c_int, "bDefault"),
                      (['out'], c_void_p, "pmftDefaultPeriod"), (['out'], c_void_p, "pmftMinimumPeriod")),
            COMMETHOD([], HRESULT, "SetProcessingPeriod",
                      (['in'], c_wchar_p, "pszDeviceName"), (['in'], c_void_p, "pmftPeriod")),
            COMMETHOD([], HRESULT, "GetShareMode",
                      (['in'], c_wchar_p, "pszDeviceName"), (['out'], c_void_p, "pMode")),
            COMMETHOD([], HRESULT, "SetShareMode",
                      (['in'], c_wchar_p, "pszDeviceName"), (['in'], c_void_p, "mode")),
            COMMETHOD([], HRESULT, "GetPropertyValue",
                      (['in'], c_wchar_p, "pszDeviceName"), (['in'], c_int, "bFxStore"),
                      (['in'], c_void_p, "key"), (['out'], c_void_p, "pv")),
            COMMETHOD([], HRESULT, "SetPropertyValue",
                      (['in'], c_wchar_p, "pszDeviceName"), (['in'], c_int, "bFxStore"),
                      (['in'], c_void_p, "key"), (['in'], c_void_p, "pv")),
            COMMETHOD([], HRESULT, "SetDefaultEndpoint",
                      (['in'], c_wchar_p, "wszDeviceId"), (['in'], c_int, "eRole")),
            COMMETHOD([], HRESULT, "SetEndpointVisibility",
                      (['in'], c_wchar_p, "pszDeviceName"), (['in'], c_int, "bVisible")),
        ]

    pythoncom.CoInitialize()
    try:
        policy_config = comtypes.CoCreateInstance(
            GUID(_CLSID_POLICY_CONFIG), IPolicyConfig, comtypes.CLSCTX_ALL
        )
        for role in _ROLES:
            policy_config.SetDefaultEndpoint(device_id, role)
    finally:
        pythoncom.CoUninitialize()
