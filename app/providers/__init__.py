from .base import Provider, RawHit, SearchRequest
from .vendor_case_studies import VendorCaseStudyProvider
from .featuredcustomers import FeaturedCustomersProvider
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
        WebSearchProvider(),
        ReviewSitesProvider(),
        JobPostingsProvider(),
        LinkedInProvider(),
        YouTubeProvider(),
        PodcastsProvider(),
    ]
