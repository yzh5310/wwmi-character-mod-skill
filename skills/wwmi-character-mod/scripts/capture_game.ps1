param(
    [Parameter(Mandatory=$true)][string]$Path,
    [string]$ProcessName = 'Client-Win64-Shipping',
    [string]$HideProcessName = 'Codex'
)
$ErrorActionPreference = 'Stop'
if (-not ('WwmiSkillCaptureNative' -as [type])) {
    Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class WwmiSkillCaptureNative {
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr value);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr handle);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr handle, int mode);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr handle);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr handle);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr handle, out RECT rect);
}
'@
}
Add-Type -AssemblyName System.Drawing
$outputPath = [System.IO.Path]::GetFullPath($Path)
if ([System.IO.Path]::GetExtension($outputPath) -ne '.png') { throw 'Output must be a .png file.' }
if (Test-Path -LiteralPath $outputPath) { throw 'Output already exists; choose a new evidence filename.' }
$gameWindows = @(Get-Process -Name $ProcessName | Where-Object {$_.MainWindowHandle -ne 0})
if ($gameWindows.Count -ne 1) { throw "Expected one game window; found $($gameWindows.Count)." }
$gameHandle = $gameWindows[0].MainWindowHandle
if ([WwmiSkillCaptureNative]::IsIconic($gameHandle)) { throw 'Restore the game window before capturing.' }
$restoreHandles = @()
if ($HideProcessName -and $HideProcessName -ne $ProcessName) {
    $restoreHandles = @(Get-Process -Name $HideProcessName -ErrorAction SilentlyContinue |
        Where-Object {$_.MainWindowHandle -ne 0 -and
            [WwmiSkillCaptureNative]::IsWindowVisible($_.MainWindowHandle) -and
            -not [WwmiSkillCaptureNative]::IsIconic($_.MainWindowHandle)} |
        ForEach-Object {$_.MainWindowHandle})
}
$priorDpi = [WwmiSkillCaptureNative]::SetThreadDpiAwarenessContext([IntPtr](-4))
$bitmap = $null
$graphics = $null
try {
    $restoreHandles | ForEach-Object {[WwmiSkillCaptureNative]::ShowWindow($_,6)|Out-Null}
    [WwmiSkillCaptureNative]::SetForegroundWindow($gameHandle)|Out-Null
    Start-Sleep -Milliseconds 400
    if ([WwmiSkillCaptureNative]::GetForegroundWindow() -ne $gameHandle) {
        throw 'Game did not become foreground; do not interpret an obscured capture as game evidence.'
    }
    $rect = New-Object WwmiSkillCaptureNative+RECT
    if (-not [WwmiSkillCaptureNative]::GetWindowRect($gameHandle,[ref]$rect)) { throw 'Cannot read game bounds.' }
    $width = $rect.Right - $rect.Left
    $height = $rect.Bottom - $rect.Top
    if ($width -le 0 -or $height -le 0) { throw 'Invalid window bounds.' }
    [System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($outputPath))|Out-Null
    $bitmap = New-Object System.Drawing.Bitmap($width,$height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($rect.Left,$rect.Top,0,0,(New-Object System.Drawing.Size($width,$height)))
    $bitmap.Save($outputPath,[System.Drawing.Imaging.ImageFormat]::Png)
    @{path=$outputPath;width=$width;height=$height;requires_visual_review=$true}|ConvertTo-Json -Compress
} finally {
    if ($graphics) {$graphics.Dispose()}
    if ($bitmap) {$bitmap.Dispose()}
    $restoreHandles | ForEach-Object {[WwmiSkillCaptureNative]::ShowWindow($_,9)|Out-Null}
    if ($priorDpi -ne [IntPtr]::Zero) {[WwmiSkillCaptureNative]::SetThreadDpiAwarenessContext($priorDpi)|Out-Null}
}
