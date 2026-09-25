import { ApiError } from '../api/client'

function describe(error: unknown): { title: string; message: string } {
  if (error instanceof ApiError) {
    if (error.isNetworkError) {
      return {
        title: "Can't reach the server",
        message: 'Check your connection, or whether the API is running, then try again.',
      }
    }
    if (error.status >= 500) {
      return { title: 'Something went wrong', message: 'The server hit an unexpected error.' }
    }
    return { title: 'Request failed', message: error.message }
  }
  return { title: 'Something went wrong', message: 'An unexpected error occurred.' }
}

export default function ErrorState({
  error,
  onRetry,
  retrying = false,
}: {
  error: unknown
  onRetry?: () => void
  retrying?: boolean
}) {
  const { title, message } = describe(error)
  const requestId = error instanceof ApiError ? error.requestId : null

  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-6 py-8 text-center">
      <h2 className="text-sm font-semibold text-red-800">{title}</h2>
      <p className="mt-1 text-sm text-red-700">{message}</p>
      {requestId && (
        // Lets a user or support engineer find this exact request in the server logs.
        <p className="mt-2 text-xs text-red-700/80">
          Request ID: <code className="select-all font-mono">{requestId}</code>
        </p>
      )}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          disabled={retrying}
          className="mt-4 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-red-800 ring-1 ring-red-300 hover:bg-red-100 disabled:opacity-60"
        >
          {retrying ? 'Retrying…' : 'Try again'}
        </button>
      )}
    </div>
  )
}
