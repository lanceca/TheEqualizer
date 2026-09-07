import { useEffect } from 'react'
import './FormErrorEnhancer.css'

const FIELD_WRAPPER_SELECTORS = [
  '.account-form-field',
  '.form-field',
  '.field-group',
  '.login-field',
  '.security-page form p',
  '.article-form-field',
  '.editorial-form-field',
  '.profile-form-field',
  '.request-form-field',
].join(', ')

const CONTROL_SELECTOR = [
  'input:not([type="hidden"])',
  'select',
  'textarea',
].join(', ')

const SERVER_ERROR_SELECTOR = [
  '.form-errors',
  '.errorlist',
  '[data-field-errors]',
].join(', ')

function createErrorId(control) {
  if (control.id) {
    return `${control.id}-equalizer-error`
  }

  const name =
    control.getAttribute('name')
    || 'field'

  return (
    `${name.replace(/[^a-zA-Z0-9_-]/g, '-')}`
    + '-equalizer-error'
  )
}

function connectErrorToControl(
  control,
  errorElement,
) {
  if (!control || !errorElement) {
    return
  }

  control.classList.add(
    'equalizer-field-invalid',
  )

  control.setAttribute(
    'aria-invalid',
    'true',
  )

  if (!errorElement.id) {
    errorElement.id =
      createErrorId(control)
  }

  const describedBy = new Set(
    (
      control.getAttribute(
        'aria-describedby',
      )
      || ''
    )
      .split(/\s+/)
      .filter(Boolean),
  )

  describedBy.add(errorElement.id)

  control.setAttribute(
    'aria-describedby',
    Array.from(describedBy).join(' '),
  )
}

function clearClientError(control) {
  control.classList.remove(
    'equalizer-client-invalid',
  )

  if (
    !control.classList.contains(
      'equalizer-field-invalid',
    )
  ) {
    control.removeAttribute(
      'aria-invalid',
    )
  }

  const wrapper =
    control.closest(
      FIELD_WRAPPER_SELECTORS,
    )
    || control.parentElement

  if (!wrapper) {
    return
  }

  wrapper
    .querySelectorAll(
      '.equalizer-client-error',
    )
    .forEach(
      (element) => element.remove(),
    )
}

function showClientError(control) {
  if (
    !control
    || !control.validationMessage
  ) {
    return
  }

  control.classList.add(
    'equalizer-client-invalid',
  )

  control.setAttribute(
    'aria-invalid',
    'true',
  )

  const wrapper =
    control.closest(
      FIELD_WRAPPER_SELECTORS,
    )
    || control.parentElement

  if (!wrapper) {
    return
  }

  let errorElement =
    wrapper.querySelector(
      '.equalizer-client-error',
    )

  if (!errorElement) {
    errorElement =
      document.createElement('div')

    errorElement.className =
      'equalizer-client-error'

    errorElement.setAttribute(
      'role',
      'alert',
    )

    const icon =
      document.createElement('span')

    icon.className =
      'equalizer-field-error-icon'

    icon.setAttribute(
      'aria-hidden',
      'true',
    )

    icon.textContent = '!'

    const message =
      document.createElement('span')

    message.className =
      'equalizer-field-error-text'

    errorElement.appendChild(icon)
    errorElement.appendChild(message)

    wrapper.appendChild(
      errorElement,
    )
  }

  const message =
    errorElement.querySelector(
      '.equalizer-field-error-text',
    )

  if (message) {
    message.textContent =
      control.validationMessage
  }

  connectErrorToControl(
    control,
    errorElement,
  )
}

function normalizeServerError(
  errorElement,
) {
  if (
    !errorElement
    || errorElement.dataset
      .equalizerEnhanced === 'true'
  ) {
    return
  }

  errorElement.dataset
    .equalizerEnhanced = 'true'

  errorElement.classList.add(
    'equalizer-server-error',
  )

  errorElement.setAttribute(
    'role',
    'alert',
  )

  const isNonFieldError =
    errorElement.classList.contains(
      'nonfield',
    )
    || errorElement.closest(
      '.non-field-errors',
    )

  if (isNonFieldError) {
    errorElement.classList.add(
      'equalizer-non-field-error',
    )

    return
  }

  const wrapper =
    errorElement.closest(
      FIELD_WRAPPER_SELECTORS,
    )
    || errorElement.parentElement

  if (!wrapper) {
    return
  }

  wrapper.classList.add(
    'equalizer-field-has-error',
  )

  const controls =
    wrapper.querySelectorAll(
      CONTROL_SELECTOR,
    )

  controls.forEach(
    (control) => {
      connectErrorToControl(
        control,
        errorElement,
      )
    },
  )
}

function enhanceExistingErrors(root) {
  const scope =
    root instanceof Element
      ? root
      : document

  scope
    .querySelectorAll(
      SERVER_ERROR_SELECTOR,
    )
    .forEach(
      normalizeServerError,
    )

  if (
    scope instanceof Element
    && scope.matches(
      SERVER_ERROR_SELECTOR,
    )
  ) {
    normalizeServerError(scope)
  }
}

function FormErrorEnhancer() {
  useEffect(() => {
    enhanceExistingErrors(document)

    function handleInvalid(event) {
      const control = event.target

      if (
        !(control instanceof HTMLElement)
        || !control.matches(
          CONTROL_SELECTOR,
        )
      ) {
        return
      }

      showClientError(control)
    }

    function handleInput(event) {
      const control = event.target

      if (
        !(control instanceof HTMLElement)
        || !control.matches(
          CONTROL_SELECTOR,
        )
      ) {
        return
      }

      if (control.checkValidity()) {
        clearClientError(control)
      }
    }

    document.addEventListener(
      'invalid',
      handleInvalid,
      true,
    )

    document.addEventListener(
      'input',
      handleInput,
      true,
    )

    document.addEventListener(
      'change',
      handleInput,
      true,
    )

    const observer =
      new MutationObserver(
        (mutations) => {
          mutations.forEach(
            (mutation) => {
              mutation.addedNodes
                .forEach(
                  (node) => {
                    if (
                      node instanceof Element
                    ) {
                      enhanceExistingErrors(
                        node,
                      )
                    }
                  },
                )
            },
          )
        },
      )

    observer.observe(
      document.body,
      {
        childList: true,
        subtree: true,
      },
    )

    return () => {
      document.removeEventListener(
        'invalid',
        handleInvalid,
        true,
      )

      document.removeEventListener(
        'input',
        handleInput,
        true,
      )

      document.removeEventListener(
        'change',
        handleInput,
        true,
      )

      observer.disconnect()
    }
  }, [])

  return null
}

export default FormErrorEnhancer
