from .base import Provider, RawHit, SearchRequest
from .vendor_case_studies import VendorCaseStudyProvider
from .featuredcustomers import FeaturedCustomersProvider
from .g2 import G2Provider
from .peerspot import PeerSpotProvider
from .trustradius import TrustRadiusProvider
from .web_search import WebSearchProvider
from .review_sites import ReviewSitesProvider
from .job_postings import JobPostingsProvider
from .linkedin import LinkedInProvider
from .youtube import YouTubeProvider
from .podcasts import PodcastsProvider


def all_providers() -> list[Provider]:
    return [
        VendorCaseStudyProvider(),
        FeaturedCustomersProvider(),
        G2Provider(),
        PeerSpotProvider(),
        TrustRadiusProvider(),
        WebSearchProvider(),
        ReviewSitesProvider(),
        JobPostingsProvider(),
        LinkedInProvider(),
        YouTubeProvider(),
        PodcastsProvider(),
    ]
