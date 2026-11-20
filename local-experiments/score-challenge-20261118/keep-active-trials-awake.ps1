# Reset the system idle timer only while a local score trial is running on AC.
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
public static class TrialPower {
    [DllImport("kernel32.dll")]
    public static extern uint SetThreadExecutionState(uint flags);
}
'@
while ($true) {
    $jobs = Get-CimInstance Win32_Process -Filter "Name='wsl.exe'" | Where-Object {
        $_.CommandLine -match '/aic-eda-task2/local-experiments/.+/(measure_train_score|run_challengers|test_changed_cells|promote_training_probe|measure_development_panel|run_public_development|measure_fifteen)\.py' -or
            $_.CommandLine -match '/aic-eda-task2/trial_baseline\.py --(public-validation|development-validation-cell)\b'
    }
    if (-not $jobs) { break }
    if ([System.Windows.Forms.SystemInformation]::PowerStatus.PowerLineStatus -eq 'Online') {
        [void][TrialPower]::SetThreadExecutionState(1)
    }
    Start-Sleep -Seconds 30
}
