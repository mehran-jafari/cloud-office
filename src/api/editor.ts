import { apiFetch } from './client';
import type { FileVersion, OnlyOfficeEditorConfig } from '../types/api';
export function getEditorConfig(fileId: string | number) { return apiFetch<OnlyOfficeEditorConfig>(`/files/${fileId}/editor-config/`); }
export function getFileVersions(fileId: string | number) { return apiFetch<FileVersion[]>(`/files/${fileId}/versions/`); }
