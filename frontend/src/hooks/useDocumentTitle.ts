import { useEffect } from 'react'

const APP_NAME = 'Lead Intake'

/** Sets the browser tab title ("Rahul Sharma · Lead Intake") while the page is shown. */
export function useDocumentTitle(title: string | undefined) {
  useEffect(() => {
    document.title = title ? `${title} · ${APP_NAME}` : APP_NAME
  }, [title])
}
