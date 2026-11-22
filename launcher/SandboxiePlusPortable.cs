// Copyright (c) 2026 Portable builder contributors. Original source distributed under MIT.
// Transparent .NET Framework 4.x WinExe launcher. Does not install/remove a driver or service.
// Data and recovery records remain next to the executable. No registry writes or shell hooks.
using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Diagnostics;
using System.Threading;
using System.Collections.Generic;
using Microsoft.Win32;
using System.Windows.Forms;

internal static class SandboxiePlusPortable {
    static string Root, App, Data, Config, Guard;
    static HashSet<string> Baseline = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
    static readonly string[] Settings = { "Sandboxie.ini", "Sandboxie-Plus.ini" };
    static readonly HashSet<string> SafeExtensions = new HashSet<string>(new [] { ".ini", ".json", ".log", ".db", ".sqlite", ".sqlite3", ".txt", ".xml", ".cfg", ".dat", ".yaml", ".yml" }, StringComparer.OrdinalIgnoreCase);
    static readonly string[] SystemServiceNames = {"SbieDrv", "SbieSvc"};
    static string Active { get { return Path.Combine(Guard,"session.active"); } }
    static void Warn(string msg) { MessageBox.Show(msg,"Sandboxie Plus Portable",MessageBoxButtons.OK,MessageBoxIcon.Warning); }
    static string Clean(string path) {return Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar);}
    static bool IsSubpath(string path,string parent) {
        string p = Clean(path), d=Clean(parent);
        return p.StartsWith(d+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase);
    }
    static bool Reparse(string path) {
        return (File.GetAttributes(path)&FileAttributes.ReparsePoint)!=0;
    }
    static void EnsureNoLinks(string path) {
        if(!IsSubpath(path,Root) && !string.Equals(Clean(path),Clean(Root),StringComparison.OrdinalIgnoreCase)) throw new IOException("Attempt to use a nonportable path: "+path);
        string cur=path;
        while(cur.Length >= Root.Length && IsSubpath(cur,Root)) {
            if((File.Exists(cur)||Directory.Exists(cur)) && Reparse(cur))throw new IOException("Reparse point / symlink not allowed in portable managed tree: "+cur);
            cur=Path.GetDirectoryName(cur);
            if(cur==null)break;
        }
    }
    static void AtomicCopy(string from,string to) {
        EnsureNoLinks(from);EnsureNoLinks(to);
        Directory.CreateDirectory(Path.GetDirectoryName(to));
        string temp=to+".tg-new-"+Guid.NewGuid().ToString("N");
        try{
            File.Copy(from,temp,false);
            if(File.Exists(to)){
                string backup=to+".tg-previous";
                File.Replace(temp,to,backup,true); // Local filesystem atomic replacement with previous copy.
            }else File.Move(temp,to);
        }finally{ if(File.Exists(temp))File.Delete(temp); }
    }
    static void RecoverSettings() {
        bool previousCrashed=File.Exists(Active);
        Directory.CreateDirectory(Config);
        string def=Path.Combine(Root,"App","DefaultData","Config");
        foreach(string name in Settings){
            string local=Path.Combine(App,name),saved=Path.Combine(Config,name),initial=Path.Combine(def,name);
            if(!File.Exists(initial))throw new IOException("Missing default portable configuration: "+initial);
            // Preserve anything left by an interrupted SandMan run, before reinitialization.
            if(previousCrashed && File.Exists(local)){
                if(File.Exists(saved) && !Same(local,saved)) {
                    string rev=Path.Combine(Guard,"Recovery",DateTime.UtcNow.ToString("yyyyMMddTHHmmssfff")+"-"+name);
                    Directory.CreateDirectory(Path.GetDirectoryName(rev));
                    AtomicCopy(saved,rev);
                }
                AtomicCopy(local,saved);
            }
            if(!File.Exists(saved)) AtomicCopy(initial,saved);
            AtomicCopy(saved,local);
        }
        if(previousCrashed) Log("Recovered config files left by an interrupted prior session. Previous versions backed up when different.");
    }
    static bool Same(string a,string b) {
        FileInfo af=new FileInfo(a),bf=new FileInfo(b);if(af.Length!=bf.Length)return false;
        using(FileStream f=File.OpenRead(a)) using(FileStream g=File.OpenRead(b)){
            byte[] x=new byte[65536],y=new byte[65536];int n;
            while((n=f.Read(x,0,x.Length))>0){if(g.Read(y,0,n)!=n)return false;for(int i=0;i<n;i++)if(x[i]!=y[i])return false;}
        }return true;
    }
    static void Log(string message) {
        Directory.CreateDirectory(Guard);
        File.AppendAllText(Path.Combine(Guard,"events.log"),DateTime.UtcNow.ToString("o")+" "+message+Environment.NewLine,Encoding.UTF8);
    }
    static void VerifyHost() {
        string hostIni=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows),"Sandboxie.ini");
        if(File.Exists(hostIni)) throw new IOException("A system-wide Sandboxie.ini exists at "+hostIni+". It takes precedence over portable configuration. No changes made. Use separate Windows installation or consult the upstream migration guide.");
        foreach(var name in SystemServiceNames){
            using(RegistryKey k=Registry.LocalMachine.OpenSubKey(@"SYSTEM\CurrentControlSet\Services\"+name)){
                if(k==null) continue;
                string image=(k.GetValue("ImagePath")??"").ToString().Replace('"',' ').Trim();
                if(image.StartsWith(@"\??\"))image=image.Substring(4);
                // Refuse to take ownership of a pre-existing unrelated service/driver.
                if(!image.ToLowerInvariant().Contains(App.ToLowerInvariant()))
                    throw new IOException("Detected existing "+name+" registered to a different installation ("+image+"). Cannot safely mix Sandboxie drivers/services. No host changes made.");
            }
        }
    }
    static void GetBaseline() {
        string f=Path.Combine(Root,"App","AppInfo","payload-files.json");
        if(!File.Exists(f))throw new IOException("Missing packaged payload-files.json");
        string data=File.ReadAllText(f);
        // JSON is an array of escaped paths; use .NET built-in serializer only if available.
        var js=new System.Web.Script.Serialization.JavaScriptSerializer();
        foreach(string item in js.Deserialize<string[]>(data))Baseline.Add(item.Replace('/','\\'));
    }
    static IEnumerable<string> Walk(string dir) {
        if(!Directory.Exists(dir))yield break;
        Stack<string> stack=new Stack<string>();stack.Push(dir);
        while(stack.Count>0){string current=stack.Pop();EnsureNoLinks(current);
            foreach(string path in Directory.GetFileSystemEntries(current)) {
                EnsureNoLinks(path);yield return path;
                if(Directory.Exists(path))stack.Push(path);
            }
        }
    }
    static void RestoreOwned() {
        string recovered=Path.Combine(Guard,"RecoveredPaths");
        if(!Directory.Exists(recovered))return;
        foreach(string item in Walk(recovered)){
            string rel=item.Substring(recovered.Length).TrimStart('\\');
            if(string.IsNullOrEmpty(rel))continue;
            string dst=Path.Combine(App,rel);
            EnsureNoLinks(dst);
            if(Directory.Exists(item)){Directory.CreateDirectory(dst);continue;}
            if(SafeExtensions.Contains(Path.GetExtension(item)) && !File.Exists(dst))AtomicCopy(item,dst);
        }
    }
    static void SnapshotOwned() {
        string recovered=Path.Combine(Guard,"RecoveredPaths");
        foreach(string item in Walk(App)){
            string rel=item.Substring(App.Length).TrimStart('\\');
            if(string.IsNullOrEmpty(rel)||Settings.Contains(rel,StringComparer.OrdinalIgnoreCase))continue;
            if(Directory.Exists(item)){
                if(!Directory.EnumerateFileSystemEntries(item).Any()) {
                    string dst=Path.Combine(recovered,rel);EnsureNoLinks(dst);Directory.CreateDirectory(dst);
                }
            }else if(!Baseline.Contains(rel)){
                if(SafeExtensions.Contains(Path.GetExtension(item))){
                    string dst=Path.Combine(recovered,rel);AtomicCopy(item,dst);
                    Log("Preserved newly created non-executable application path: "+rel);
                }else {Log("MANUAL REVIEW: unexpected binary or unknown file type found: "+rel);}
            }
        }
        // Sandbox content is kept directly in Data; journal its empty directory trees.
        string boxes=Path.Combine(Data,"Sandboxes");
        List<string> dirs=new List<string>();
        foreach(string p in Walk(boxes))if(Directory.Exists(p))dirs.Add(p.Substring(boxes.Length).TrimStart('\\'));
        dirs.Sort(StringComparer.OrdinalIgnoreCase);
        File.WriteAllLines(Path.Combine(Guard,"sandbox-directory-manifest.txt"),dirs,Encoding.UTF8);
    }
    static void SaveSettings() {
        foreach(string name in Settings) {
            string src=Path.Combine(App,name),dst=Path.Combine(Config,name);
            if(!File.Exists(src))throw new IOException("Upstream setting disappeared during run: "+name);
            if(!Same(src,dst))AtomicCopy(src,dst);
        }
        SnapshotOwned();
    }
    static void WaitOtherSandMan(Process launched) {
        // SandMan sometimes handoffs to an existing process. Never kill tasks or service.
        DateTime end=DateTime.UtcNow.AddMinutes(5);
        while(DateTime.UtcNow<end){
            bool stillRunning=false;
            foreach(Process p in Process.GetProcessesByName("SandMan")){
                try{
                    if(p.Id==Process.GetCurrentProcess().Id)continue;
                    if(IsSubpath(p.MainModule.FileName,App)){stillRunning=true;break;}
                }catch(System.ComponentModel.Win32Exception){
                    // Elevated process can be inaccessible to a non-elevated launcher.
                    Log("Cannot read an elevated SandMan process path; do not claim complete child tracking.");
                }catch(InvalidOperationException){}
                finally{p.Dispose();}
            }
            if(!stillRunning)return;
            Thread.Sleep(1500);
        }
        throw new IOException("SandMan is still active after observation window; settings were not finalized. Close the UI and relaunch for crash recovery.");
    }
    [STAThread] static int Main(string[] args) {
        bool activeWritten=false;
        try{
            Root=Clean(AppDomain.CurrentDomain.BaseDirectory);
            App=Path.Combine(Root,"App","Sandboxie");Data=Path.Combine(Root,"Data");Config=Path.Combine(Data,"Config");Guard=Path.Combine(Data,"TraceGuard");
            if(!Directory.Exists(App)||!File.Exists(Path.Combine(App,"SandMan.exe")))throw new IOException("Sandboxie application payload not found");
            Directory.CreateDirectory(Data); Directory.CreateDirectory(Guard);Directory.CreateDirectory(Path.Combine(Data,"Sandboxes"));
            string mutexKey=Convert.ToBase64String(System.Security.Cryptography.SHA256.Create().ComputeHash(Encoding.UTF8.GetBytes(Root.ToLowerInvariant()))).Replace('/','_').Replace('+','-').Substring(0,24);
            bool created;using(Mutex mutex=new Mutex(true,"Local\\SandboxiePortable_"+mutexKey,out created)) {
                if(!created)throw new IOException("This portable folder is already running. Do not start two sessions using the same Data.");
                VerifyHost();GetBaseline();RecoverSettings();RestoreOwned();
                File.WriteAllText(Active,DateTime.UtcNow.ToString("o"));activeWritten=true;
                ProcessStartInfo info=new ProcessStartInfo(Path.Combine(App,"SandMan.exe"));
                info.WorkingDirectory=App;info.UseShellExecute=true;
                info.Arguments=string.Join(" ",args.Select(Quote));
                using(Process p=Process.Start(info)){
                    if(p==null)throw new IOException("SandMan did not start");
                    p.WaitForExit();
                    WaitOtherSandMan(p);
                }
                SaveSettings();File.Delete(Active);activeWritten=false;
                Log("Clean launcher shutdown. Note: elevated kernel driver and service may remain active.");
                return 0;
            }
        }catch(Exception e){
            try{if(Guard!=null && Directory.Exists(Guard)){Log("FAILED: "+e);if(activeWritten)Log("Crash recovery required at next launch");}}catch{}
            Warn(e.Message+"\n\nYour Data folder was not deleted. See Data\\TraceGuard\\events.log.");return 1;
        }
    }
    static string Quote(string s) {
        // Windows C runtime argument quoting: double slashes only before quotes/end.
        StringBuilder b=new StringBuilder(); b.Append('"');int slash=0;
        foreach(char c in s) {
            if(c=='\\'){slash++;continue;}
            if(c=='"') {b.Append('\\',slash*2+1);b.Append('"');slash=0;continue;}
            b.Append('\\',slash);slash=0;b.Append(c);
        }
        b.Append('\\',slash*2);b.Append('"');return b.ToString();
    }
}
