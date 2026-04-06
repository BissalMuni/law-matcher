import React from 'react'
import ReactDOM from 'react-dom/client'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'

dayjs.extend(utc)
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import { SyncProvider } from './contexts/SyncContext'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <SyncProvider>
        <App />
      </SyncProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)
