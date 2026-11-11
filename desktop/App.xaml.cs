using System.Threading;
using System.Windows;

namespace Banklycs.App;

public partial class App : Application
{
    private static Mutex? _singleInstanceMutex;

    protected override void OnStartup(StartupEventArgs e)
    {
        // Single instance: a second launch just focuses nothing and exits quietly.
        _singleInstanceMutex = new Mutex(true, "Local\\Banklycs.StudioConsole.SingleInstance", out bool createdNew);
        if (!createdNew)
        {
            MessageBox.Show(
                "Banklycs sudah berjalan.\nGunakan aplikasi yang sudah terbuka di taskbar.",
                "Banklycs",
                MessageBoxButton.OK,
                MessageBoxImage.Information);
            Shutdown(0);
            return;
        }

        base.OnStartup(e);
    }
}
