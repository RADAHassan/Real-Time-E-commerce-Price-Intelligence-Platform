"""
Shared fixtures for scraper tests.
fake_response() builds a Scrapy TextResponse from raw HTML without any network call.
"""

import pytest
from scrapy.http import Request, TextResponse


def fake_response(url: str, html: str) -> TextResponse:
    """Return a TextResponse populated with the given HTML string."""
    request = Request(url=url)
    return TextResponse(
        url=url,
        body=html.encode("utf-8"),
        encoding="utf-8",
        request=request,
    )


@pytest.fixture
def books_listing_html():
    return """
    <html><body>
      <ol class="row">
        <article class="product_pod">
          <h3><a href="../a-light-in-the-attic_1000/index.html" title="A Light in the Attic">
            A Light in the...
          </a></h3>
          <p class="price_color">£51.77</p>
        </article>
        <article class="product_pod">
          <h3><a href="../tipping-the-velvet_999/index.html" title="Tipping the Velvet">
            Tipping the Velvet
          </a></h3>
          <p class="price_color">£53.74</p>
        </article>
      </ol>
      <li class="next"><a href="page-2.html">next</a></li>
    </body></html>
    """


@pytest.fixture
def books_detail_html():
    return """
    <html><body>
      <ul class="breadcrumb">
        <li><a href="/">Home</a></li>
        <li><a href="/catalogue/category/books_1/">Books</a></li>
        <li><a href="/catalogue/category/books/poetry_23/">Poetry</a></li>
        <li class="active">A Light in the Attic</li>
      </ul>
      <div class="product_main">
        <h1>A Light in the Attic</h1>
        <p class="price_color">£51.77</p>
        <p class="star-rating Three"></p>
        <p class="availability">
          In stock
        </p>
      </div>
      <div id="product_gallery">
        <img src="../../media/cache/2c/da/cover.jpg" alt="cover">
      </div>
    </body></html>
    """


@pytest.fixture
def scrapeme_listing_html():
    return """
    <html><body>
      <ul class="products">
        <li class="product">
          <a class="woocommerce-loop-product__link"
             href="https://scrapeme.live/shop/bulbasaur/">
            <img src="https://scrapeme.live/wp-content/uploads/bulbasaur.png">
            <h2>Bulbasaur</h2>
            <span class="price">£63.00</span>
          </a>
        </li>
        <li class="product">
          <a class="woocommerce-loop-product__link"
             href="https://scrapeme.live/shop/ivysaur/">
            <h2>Ivysaur</h2>
          </a>
        </li>
      </ul>
      <a class="next page-numbers" href="https://scrapeme.live/shop/page/2/">→</a>
    </body></html>
    """


@pytest.fixture
def scrapeme_detail_html():
    return """
    <html><body>
      <h1 class="product_title entry-title">Bulbasaur</h1>
      <p class="price">
        <span class="woocommerce-Price-amount amount">
          <bdi><span class="woocommerce-Price-currencySymbol">£</span>63.00</bdi>
        </span>
      </p>
      <p class="stock in-stock">99 in stock</p>
      <span class="posted_in"><a href="/category/pokemon/">Pokémon</a></span>
      <div class="woocommerce-product-rating">
        <span class="star-rating" aria-label="4.50 out of 5"></span>
      </div>
      <div class="woocommerce-product-gallery__image">
        <a href="https://scrapeme.live/wp-content/uploads/bulbasaur-full.png">
          <img src="https://scrapeme.live/wp-content/uploads/bulbasaur.png">
        </a>
      </div>
    </body></html>
    """
