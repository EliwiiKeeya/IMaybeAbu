import requests
from abc import ABC, abstractmethod
from typing import TypedDict, List, Optional


class PJSKProfileContentBase(TypedDict, total=False):
    user: dict
    userProfile: dict
    userDeck: dict
    userCards: List[dict]
    userCharacters: List[dict]
    userChallengeLiveSoloResult: dict
    userChallengeLiveSoloStages: List[dict]
    userMusicDifficultyClearCount: List[dict]
    userCustomProfileCards: List[dict]
    userProfileHonors: List[dict]
    userHonors: List[dict]
    userBondsHonors: List[dict]
    userStoryFavorites: List[dict]
    userConfig: dict
    userMultiLiveTopScoreCount: dict
    totalPower: dict
    userHonorMissions: List[dict]


class PJSKProfileContentCN(PJSKProfileContentBase):
    pass


class PJSKProfileContentTW(PJSKProfileContentBase):
    pass


class PJSKProfileContentJP(PJSKProfileContentBase):
    isMysekaiOwnerAcceptVisit: bool


class PJSKProfileBase(ABC):
    base_url: str = ""
    headers: Optional[dict] = None

    def __init__(self):
        if self.base_url == "":
            raise ValueError("Base_url must be set.")

    @abstractmethod
    def get_profile(self, user_id: str) -> PJSKProfileContentBase:
        pass


class PJSKProfileCN(PJSKProfileBase):
    def __init__(self, base_url: str, headers: Optional[dict] = None):
        self.base_url = base_url
        self.headers = headers
        super().__init__()

    def get_profile(self, user_id: str) -> PJSKProfileContentCN:
        url = f"{self.base_url}/cn/user/{user_id}/profile"
        content = requests.get(url, headers=self.headers).json()
        return PJSKProfileContentCN(content)


class PJSKProfileTW(PJSKProfileBase):
    def __init__(self, base_url: str, headers: Optional[dict] = None):
        self.base_url = base_url
        self.headers = headers
        super().__init__()

    def get_profile(self, user_id: str) -> PJSKProfileContentTW:        
        url = f"{self.base_url}/tw/user/{user_id}/profile"
        content = requests.get(url, headers=self.headers).json()
        return PJSKProfileContentTW(content)


class PJSKProfileJP(PJSKProfileBase):
    def __init__(self, base_url: str, headers: Optional[dict] = None):
        self.base_url = base_url
        self.headers = headers
        super().__init__()

    def get_profile(self, user_id: str) -> PJSKProfileContentJP:
        url = f"{self.base_url}/jp/user/%25user_id/{user_id}/profile"
        content = requests.get(url, headers=self.headers).json()
        return PJSKProfileContentJP(content)
