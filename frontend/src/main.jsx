import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App.jsx'
import ArticleRichTextEditor from './ArticleRichTextEditor.jsx'
import AccountEmailToggle from './AccountEmailToggle.jsx'
import InlineDownloadButton from './InlineDownloadButton.jsx'
import SystemUpdatePopup from './SystemUpdatePopup.jsx'
import PublicArchiveEnhancer from './PublicArchiveEnhancer.jsx'
import SystemUpdatesEnhancer from './SystemUpdatesEnhancer.jsx'
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
  ArticleRichTextEditor,
  AccountEmailToggle,
  InlineDownloadButton,
  SystemUpdatePopup,
  PublicArchiveEnhancer,
  SystemUpdatesEnhancer,
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
  if (componentName === 'ArticleRichTextEditor') return { fieldId: mountPoint.dataset.fieldId }
  if (componentName === 'AccountEmailToggle') return { email: mountPoint.dataset.email || '' }
  if (componentName === 'InlineDownloadButton') return { url: mountPoint.dataset.url, filename: mountPoint.dataset.filename }
  if (componentName === 'SystemUpdatePopup') return { apiUrl: mountPoint.dataset.apiUrl }
  if (componentName === 'SystemUpdatesEnhancer') return { mode: mountPoint.dataset.mode || '' }
  if (componentName === 'PublicArchiveEnhancer') return {}
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
      homeUrl:
        mountPoint.dataset.homeUrl
        || '/',
      notificationUrl:
        mountPoint.dataset.notificationUrl
        || '#',
      profileUrl:
        mountPoint.dataset.profileUrl
        || '#',
      notificationCount:
        Number.parseInt(
          mountPoint.dataset.notificationCount
          || '0',
          10,
        ) || 0,
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
