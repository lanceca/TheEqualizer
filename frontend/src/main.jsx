import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App.jsx'
import AuditLogPanel from './AuditLogPanel.jsx'
import DigitalPublicationViewer from './DigitalPublicationViewer.jsx'
import DashboardEnhancer from './DashboardEnhancer.jsx'
import EditorialWorkspaceEnhancer from './EditorialWorkspaceEnhancer.jsx'
import FormErrorEnhancer from './FormErrorEnhancer.jsx'
import HeaderActions from './HeaderActions.jsx'
import PeopleAndTeams from './PeopleAndTeams.jsx'
import PageLoadingSkeleton from './PageLoadingSkeleton.jsx'
import StaffSidebarToggle from './StaffSidebarToggle.jsx'

import './index.css'

const componentRegistry = {
  ReaderTools: App,
  AuditLogPanel,
  DigitalPublicationViewer,
  DashboardEnhancer,
  EditorialWorkspaceEnhancer,
  FormErrorEnhancer,
  HeaderActions,
  PeopleAndTeams,
  PageLoadingSkeleton,
  StaffSidebarToggle,
}

function getComponentProps(
  componentName,
  mountPoint,
) {
  if (
    componentName === 'DigitalPublicationViewer'
    || componentName === 'PeopleAndTeams'
  ) {
    return {
      apiUrl:
        mountPoint.dataset.apiUrl || '',
    }
  }

  if (
    componentName === 'AuditLogPanel'
  ) {
    return {
      apiUrl:
        mountPoint.dataset.apiUrl
        || '',
      pageUrl:
        mountPoint.dataset.pageUrl
        || '',
    }
  }

  if (
    componentName === 'StaffSidebarToggle'
  ) {
    return {
      username:
        mountPoint.dataset.username
        || '',
      role:
        mountPoint.dataset.role
        || '',
    }
  }

  if (
    componentName === 'EditorialWorkspaceEnhancer'
  ) {
    return {
      mode:
        mountPoint.dataset.mode
        || 'create',
      role:
        mountPoint.dataset.role
        || '',
      statusLabel:
        mountPoint.dataset.statusLabel
        || 'Draft',
      version:
        mountPoint.dataset.version
        || '',
      hasFeaturedImage:
        mountPoint.dataset.hasFeaturedImage
        === 'true',
    }
  }

  if (
    componentName === 'HeaderActions'
  ) {
    return {
      facebookUrl:
        mountPoint.dataset.facebookUrl
        || '',
      instagramUrl:
        mountPoint.dataset.instagramUrl
        || '',
      xUrl:
        mountPoint.dataset.xUrl
        || '',
      installUrl:
        mountPoint.dataset.installUrl
        || '',
    }
  }

  return {}
}

function mountReactComponents() {
  const mountPoints =
    document.querySelectorAll(
      '[data-react-component]',
    )

  mountPoints.forEach(
    (mountPoint) => {
      const componentName =
        mountPoint.dataset.reactComponent

      const Component =
        componentRegistry[
          componentName
        ]

      if (!Component) {
        return
      }

      if (
        mountPoint.dataset
          .reactMounted === 'true'
      ) {
        return
      }

      const componentProps =
        getComponentProps(
          componentName,
          mountPoint,
        )

      const root =
        createRoot(mountPoint)

      root.render(
        <StrictMode>
          <Component
            {...componentProps}
          />
        </StrictMode>,
      )

      mountPoint.dataset.reactMounted =
        'true'
    },
  )
}

if (
  document.readyState
  === 'loading'
) {
  document.addEventListener(
    'DOMContentLoaded',
    mountReactComponents,
  )
} else {
  mountReactComponents()
}
