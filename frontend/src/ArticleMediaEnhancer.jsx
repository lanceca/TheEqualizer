import { useEffect } from 'react'
import './ArticleMediaEnhancer.css'

function enhanceImageItem(
  figure,
  index,
  total,
) {
  const image =
    figure.querySelector('img')

  if (!image) {
    return
  }

  figure.classList.add(
    'react-article-media-card',
    'react-article-media-card--image',
  )

  figure.dataset.mediaLabel =
    `Photo ${index + 1} of ${total}`

  image.classList.add(
    'react-article-media-image',
  )

  function applyOrientation() {
    if (
      !image.naturalWidth
      || !image.naturalHeight
    ) {
      return
    }

    figure.classList.remove(
      'is-landscape',
      'is-portrait',
      'is-square',
    )

    const ratio =
      image.naturalWidth
      / image.naturalHeight

    if (ratio > 1.12) {
      figure.classList.add(
        'is-landscape',
      )
    } else if (ratio < 0.88) {
      figure.classList.add(
        'is-portrait',
      )
    } else {
      figure.classList.add(
        'is-square',
      )
    }
  }

  if (image.complete) {
    applyOrientation()
  } else {
    image.addEventListener(
      'load',
      applyOrientation,
      { once: true },
    )
  }
}

function enhanceVideoItem(
  figure,
  index,
  total,
) {
  const video =
    figure.querySelector('video')

  if (!video) {
    return
  }

  figure.classList.add(
    'react-article-media-card',
    'react-article-media-card--video',
  )

  figure.dataset.mediaLabel =
    `Video ${index + 1} of ${total}`

  video.classList.add(
    'react-article-media-video',
  )
}

function enhanceMediaSection(section) {
  section.classList.add(
    'react-article-media-section',
  )

  const imageItems =
    Array.from(
      section.querySelectorAll(
        '.reader-gallery-item',
      ),
    )

  const videoItems =
    Array.from(
      section.querySelectorAll(
        '.reader-video-item',
      ),
    )

  imageItems.forEach(
    (figure, index) => {
      enhanceImageItem(
        figure,
        index,
        imageItems.length,
      )
    },
  )

  videoItems.forEach(
    (figure, index) => {
      enhanceVideoItem(
        figure,
        index,
        videoItems.length,
      )
    },
  )
}

function ArticleMediaEnhancer() {
  useEffect(() => {
    const articlePage =
      document.querySelector(
        '.reader-article-page',
      )

    if (!articlePage) {
      return undefined
    }

    articlePage.classList.add(
      'react-article-media-ready',
    )

    const sections =
      articlePage.querySelectorAll(
        '.reader-article-media-section',
      )

    sections.forEach(
      enhanceMediaSection,
    )

    return () => {
      articlePage.classList.remove(
        'react-article-media-ready',
      )
    }
  }, [])

  return null
}

export default ArticleMediaEnhancer
