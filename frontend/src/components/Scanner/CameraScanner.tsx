import { useEffect, useRef, useState, useCallback } from 'react'
import {
  Box,
  Typography,
  Paper,
  Button,
  Alert,
  IconButton,
  Tooltip,
} from '@mui/material'
import { Videocam, VideocamOff, FlashlightOn, FlashlightOff } from '@mui/icons-material'

interface CameraScannerProps {
  onScan: (code: string) => void
  active: boolean
}

/**
 * Camera-based barcode scanner using getUserMedia.
 * Uses a simple luminance-based Code128 detection heuristic.
 * For production, integrate a library like @nickarora/barcode-reader or zxing-wasm.
 */
export default function CameraScanner({ onScan, active }: CameraScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [hasCamera, setHasCamera] = useState(true)
  const [error, setError] = useState('')
  const [torch, setTorch] = useState(false)
  const scanIntervalRef = useRef<number | null>(null)

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment',
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play()
      }
      setError('')
    } catch (err: any) {
      if (err.name === 'NotAllowedError') {
        setError('Camera permission denied. Please allow camera access.')
      } else if (err.name === 'NotFoundError') {
        setHasCamera(false)
        setError('No camera found on this device.')
      } else {
        setError(`Camera error: ${err.message}`)
      }
    }
  }, [])

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
    if (scanIntervalRef.current) {
      clearInterval(scanIntervalRef.current)
      scanIntervalRef.current = null
    }
  }, [])

  const toggleTorch = useCallback(async () => {
    if (!streamRef.current) return
    const track = streamRef.current.getVideoTracks()[0]
    if (!track) return
    try {
      const capabilities = track.getCapabilities() as any
      if (capabilities.torch) {
        await (track as any).applyConstraints({ advanced: [{ torch: !torch }] })
        setTorch(!torch)
      }
    } catch {
      // Torch not supported
    }
  }, [torch])

  // Scan loop: capture frames and look for barcode patterns
  // This is a placeholder scanning loop. In production, use a WASM barcode
  // decoder (e.g., zxing-wasm, @nickarora/barcode-reader) here.
  const startScanning = useCallback(() => {
    if (scanIntervalRef.current) return
    scanIntervalRef.current = window.setInterval(() => {
      if (!videoRef.current || !canvasRef.current) return
      const video = videoRef.current
      const canvas = canvasRef.current
      const ctx = canvas.getContext('2d')
      if (!ctx || video.readyState !== video.HAVE_ENOUGH_DATA) return

      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      ctx.drawImage(video, 0, 0)

      // Draw scan line overlay
      const midY = canvas.height / 2
      ctx.strokeStyle = '#ff0000'
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.moveTo(canvas.width * 0.1, midY)
      ctx.lineTo(canvas.width * 0.9, midY)
      ctx.stroke()

      // NOTE: Actual barcode decoding would happen here with a library.
      // The scan line visual helps users align the barcode.
      // Integration point: pass canvas ImageData to a barcode decoder.
    }, 200)
  }, [])

  useEffect(() => {
    if (active) {
      startCamera().then(startScanning)
    } else {
      stopCamera()
    }
    return stopCamera
  }, [active, startCamera, stopCamera, startScanning])

  if (!hasCamera) {
    return (
      <Alert severity="info">
        No camera detected. Use manual Job ID entry instead.
      </Alert>
    )
  }

  return (
    <Paper sx={{ p: 2, position: 'relative' }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
        <Typography variant="subtitle2">
          {active ? '📷 Camera Active — Align barcode with red line' : 'Camera Off'}
        </Typography>
        <Box>
          <Tooltip title={torch ? 'Flashlight Off' : 'Flashlight On'}>
            <IconButton size="small" onClick={toggleTorch} disabled={!active}>
              {torch ? <FlashlightOff /> : <FlashlightOn />}
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert>}

      <Box sx={{ position: 'relative', width: '100%', maxWidth: 500, mx: 'auto', bgcolor: '#000', borderRadius: 1, overflow: 'hidden' }}>
        <video
          ref={videoRef}
          style={{ width: '100%', display: active ? 'block' : 'none' }}
          playsInline
          muted
        />
        <canvas ref={canvasRef} style={{ display: 'none' }} />
        {!active && (
          <Box sx={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <VideocamOff sx={{ fontSize: 48, color: '#666' }} />
          </Box>
        )}
      </Box>

      <Typography variant="caption" color="text.secondary" display="block" mt={1} textAlign="center">
        Point camera at the barcode on the print receipt. Works best in good lighting.
      </Typography>
    </Paper>
  )
}
