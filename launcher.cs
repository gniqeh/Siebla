using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

internal static class SieblaLauncher
{
    [STAThread]
    private static void Main()
    {
        string folder = AppDomain.CurrentDomain.BaseDirectory;
        string python = Path.Combine(folder, "pythonw.exe");
        string script = Path.Combine(folder, "notebook.py");
        if (!File.Exists(python) || !File.Exists(script))
        {
            MessageBox.Show("Siebla 运行文件不完整，请重新解压发行包。", "Siebla", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }
        try
        {
            var start = new ProcessStartInfo();
            start.FileName = python;
            start.Arguments = "\"" + script + "\"";
            start.WorkingDirectory = folder;
            start.UseShellExecute = false;
            start.CreateNoWindow = true;
            Process.Start(start);
        }
        catch (Exception ex)
        {
            MessageBox.Show("无法启动 Siebla：\n" + ex.Message, "Siebla", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
