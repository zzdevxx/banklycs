using System.Threading;
using System.Windows;

namespace Banklycs.App;

public partial class App : System.Windows.Application
{
    private static Mutex? _singleInstanceMutex;
    private static EventWaitHandle? _activateSignal;

    protected override void OnStartup(StartupEventArgs e)
    {
        // Single instance: a second launch signals the first one to bring its
        // window back (ProPresenter-style) instead of nagging with a dialog.
        _singleInstanceMutex = new Mutex(true, "Local\\Banklycs.StudioConsole.SingleInstance", out bool createdNew);
        _activateSignal = new EventWaitHandle(false, EventResetMode.AutoReset, "Local\\Banklycs.StudioConsole.Activate");

        if (!createdNew)
        {
            _activateSignal.Set();
            Shutdown(0);
            return;
        }

        base.OnStartup(e);

        var listener = new Thread(() =>
        {
            while (_activateSignal.WaitOne())
            {
                Dispatcher.Invoke(() =>
                {
                    if (Current.MainWindow is MainWindow win)
                    {
                        win.RestoreFromTray();
                    }
                });
            }
        });
        listener.IsBackground = true;
        listener.Start();
    }
}
