using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using System.Web.Script.Serialization;

public class CellData {
    public string code { get; set; }
    public string output { get; set; }
}
public class NotebookData {
    public string format { get; set; }
    public List<CellData> cells { get; set; }
}
public class RunResult {
    public bool ok { get; set; }
    public string stdout { get; set; }
    public string stderr { get; set; }
}
public class CellView {
    public RichTextBox editor;
    public RichTextBox output;
}
public class SieblaWindow : Form {
    FlowLayoutPanel area = new FlowLayoutPanel();
    Label status = new Label();
    readonly List<CellView> cells = new List<CellView>();
    Process python;
    readonly object ioLock = new object();
    readonly JavaScriptSerializer json = new JavaScriptSerializer();
    volatile bool busy;

    public SieblaWindow() {
        Text = "Siebla · Python 离线笔记本";
        Width = 1024; Height = 740; MinimumSize = new Size(650, 400);
        Font = new Font("Microsoft YaHei UI", 9);
        var top = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 45, FlowDirection = FlowDirection.LeftToRight };
        AddButton(top, "＋ 单元格", (s,e) => AddCell(""));
        AddButton(top, "▶ 全部运行", (s,e) => RunAll());
        AddButton(top, "保存", (s,e) => SaveBook());
        AddButton(top, "打开", (s,e) => OpenBook());
        AddButton(top, "加载 DLC", (s,e) => LoadDlc());
        AddButton(top, "已加载 DLC", (s,e) => ShowDlc());
        AddButton(top, "告诉大模型我能干啥", (s,e) => ShowAiCapabilities());
        area.Dock = DockStyle.Fill;
        area.AutoScroll = true;
        area.FlowDirection = FlowDirection.TopDown;
        area.WrapContents = false;
        area.Padding = new Padding(10);
        area.Resize += (s,e) => ResizeCells();
        status.Dock = DockStyle.Bottom; status.Height = 25; status.Text = "就绪 · 完全离线";
        Controls.Add(area); Controls.Add(top); Controls.Add(status);
        var info = new ProcessStartInfo(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "python.exe"));
        info.Arguments = "-u runner.py";
        info.WorkingDirectory = AppDomain.CurrentDomain.BaseDirectory;
        info.UseShellExecute = false;
        info.CreateNoWindow = true;
        info.RedirectStandardInput = true;
        info.RedirectStandardOutput = true;
        info.RedirectStandardError = true;
        python = Process.Start(info);
        AddCell("import sys\nprint('Python', sys.version.split()[0])\nprint('解释器', sys.executable)");
    }
    void AddButton(FlowLayoutPanel p, string label, EventHandler click) {
        var b = new Button { Text = label, AutoSize = true, Height = 30 };
        b.Click += click; p.Controls.Add(b);
    }
    CellView AddCell(string text) {
        var frame = new Panel { Height = 242, Width = Math.Max(400, area.ClientSize.Width - 42),
            BorderStyle = BorderStyle.FixedSingle, Margin = new Padding(0,0,0,10) };
        var label = new Label { Text = "In [" + (cells.Count+1) + "]", Left = 8, Top = 6, AutoSize = true };
        var run = new Button { Text = "▶ 运行", Width = 85, Height = 28, Top = 3, Left = 80 };
        var editor = new RichTextBox { Left = 8, Top = 34, Width = frame.Width-18, Height = 115,
            Text = text, Font = new Font("Consolas", 10), WordWrap = false,
            Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right };
        var output = new RichTextBox { Left = 8, Top = 159, Width = frame.Width-18, Height = 72,
            ReadOnly = true, BackColor = Color.FromArgb(248,249,251),
            Font = new Font("Consolas", 9), WordWrap = false,
            Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right };
        var cell = new CellView { editor = editor, output = output };
        run.Click += (s,e) => RunCell(cell);
        editor.KeyDown += (s,e) => {
            if (e.KeyCode == Keys.Enter && e.Shift) {
                e.SuppressKeyPress = true; e.Handled = true;
                RunCell(cell);
            }
        };
        frame.Controls.Add(label); frame.Controls.Add(run);
        frame.Controls.Add(editor); frame.Controls.Add(output);
        cells.Add(cell); area.Controls.Add(frame);
        return cell;
    }
    void ResizeCells() {
        foreach (Control child in area.Controls)
            child.Width = Math.Max(400, area.ClientSize.Width - 36);
    }
    void RunCell(CellView cell, Action complete = null) {
        if (busy) return;
        busy = true;
        status.Text = "运行中…";
        string code = cell.editor.Text;
        ThreadPool.QueueUserWorkItem(_ => {
            RunResult result = null;
            string error = null;
            try {
                lock(ioLock) {
                    python.StandardInput.WriteLine(Convert.ToBase64String(Encoding.UTF8.GetBytes(code)));
                    python.StandardInput.Flush();
                    string line = python.StandardOutput.ReadLine();
                    if(line == null) throw new Exception("Python 执行器已退出");
                    result = json.Deserialize<RunResult>(
                        Encoding.UTF8.GetString(Convert.FromBase64String(line)));
                }
            } catch(Exception ex) { error = ex.ToString(); }
            if(!IsDisposed && IsHandleCreated) BeginInvoke((Action)(() => {
                cell.output.Text = error ?? ((result.stdout ?? "") + (result.stderr ?? ""));
                status.Text = error == null && result.ok ? "执行成功" : "执行失败";
                busy = false;
                if(complete != null) complete();
            }));
        });
    }
    void RunAll() {
        int i = 0;
        Action next = null;
        next = () => { if(i < cells.Count) RunCell(cells[i++], next); };
        next();
    }
    void ShowAiCapabilities() {
        var cell = AddCell("from capabilities import describe_environment\\nprint(describe_environment())");
        RunCell(cell);
        status.Text = "说明将显示在新单元格输出区，可选择复制";
    }
    void ShowDlc() {
        // Uses the shared Python backend and displays the result in the notebook.
        var cell = AddCell("import dlc\nprint(dlc.installed_summary())");
        RunCell(cell);
    }
    void LoadDlc() {
        using(var dialog = new OpenFileDialog { Filter = "Siebla 扩展包|*.zip", Title = "选择离线 DLC ZIP" }) {
            if(dialog.ShowDialog() != DialogResult.OK) return;
            // Python json literal provides safe quoting for arbitrary local paths.
            string pathLiteral = json.Serialize(dialog.FileName);
            var cell = AddCell("import dlc\ndlc.install(" + pathLiteral + ")");
            RunCell(cell);
        }
    }
    void SaveBook() {
        using(var dialog = new SaveFileDialog { Filter = "Siebla 笔记本|*.json",
              FileName = "我的笔记本.json" }) {
            if(dialog.ShowDialog() != DialogResult.OK) return;
            var book = new NotebookData { format="siebla-notebook-v1", cells=new List<CellData>() };
            foreach(var cell in cells) book.cells.Add(new CellData { code=cell.editor.Text, output=cell.output.Text });
            File.WriteAllText(dialog.FileName, json.Serialize(book), Encoding.UTF8);
            status.Text = "保存完成";
        }
    }
    void OpenBook() {
        using(var dialog = new OpenFileDialog { Filter = "Siebla 笔记本|*.json" }) {
            if(dialog.ShowDialog() != DialogResult.OK) return;
            try {
                var book = json.Deserialize<NotebookData>(File.ReadAllText(dialog.FileName, Encoding.UTF8));
                if(book == null || book.format != "siebla-notebook-v1" || book.cells == null)
                    throw new Exception("不支持的笔记本格式");
                cells.Clear(); area.Controls.Clear();
                foreach(var data in book.cells) {
                    var cell = AddCell(data.code ?? "");
                    cell.output.Text = data.output ?? "";
                }
                if(cells.Count == 0) AddCell("");
                status.Text = "打开完成";
            } catch(Exception ex) { MessageBox.Show(ex.Message, "文件读取失败"); }
        }
    }
    protected override void OnFormClosed(FormClosedEventArgs e) {
        try {
            if(python != null && !python.HasExited) python.Kill();
            if(python != null) python.Dispose();
        } catch { }
        base.OnFormClosed(e);
    }
    [STAThread]
    public static void Main() {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        try { Application.Run(new SieblaWindow()); }
        catch(Exception ex) { MessageBox.Show(ex.ToString(), "Siebla 启动失败"); }
    }
}
