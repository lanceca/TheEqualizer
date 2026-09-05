import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import DigitalPublicationViewer from './DigitalPublicationViewer.jsx'
import PeopleAndTeams from './PeopleAndTeams.jsx'
import './index.css'

const componentRegistry = {
  ReaderTools: App,
  DigitalPublicationViewer,
  PeopleAndTeams,
}

function getComponentProps(
  componentName,
  mountPoint,
) {
  if (
    componentName === 'DigitalPublicationViewer' ||
    componentName === 'PeopleAndTeams'
  ) {
    return {
      apiUrl: mountPoint.dataset.apiUrl || '',
    }
  }

  return {}
}

function mountReactComponents() {
  const mountPoints = document.querySelectorAll(
    '[data-react-component]',
  )

  mountPoints.forEach((mountPoint) => {
    const componentName =
      mountPoint.dataset.reactComponent

    const Component =
      componentRegistry[componentName]

    if (!Component) {
      return
    }

    if (mountPoint.dataset.reactMounted === 'true') {
      return
    }

    const componentProps = getComponentProps(
      componentName,
      mountPoint,
    )

    const root = createRoot(mountPoint)

    root.render(
      <StrictMode>
        <Component {...componentProps} />
      </StrictMode>,
    )

    mountPoint.dataset.reactMounted = 'true'
  })
}

if (document.readyState === 'loading') {
  document.addEventListener(
    'DOMContentLoaded',
    mountReactComponents,
  )
} else {
  mountReactComponents()
}
