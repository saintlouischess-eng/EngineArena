using System.Runtime.InteropServices;
using System.Diagnostics;
using System.IO.Pipes;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text.Json;
using LibreHardwareMonitor.Hardware;
using LibreHardwareMonitor.PawnIo;
using Microsoft.Win32.SafeHandles;

namespace EngineArena.Sensors;

internal static class Program
{
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern SafeFileHandle CreateFile(string name,uint access,uint share,IntPtr security,uint mode,uint flags,IntPtr template);

    static void Reply(object value)=>Console.WriteLine(JsonSerializer.Serialize(value));

    static async Task Main(string[] args)
    {
        try
        {
            if(args.Length==6 && args[0]=="--serve")
            {
                await Serve(args);
                return;
            }
            if(args.Length!=0)throw new ArgumentException("Invalid sensor reader arguments.");
            var pipe=Environment.GetEnvironmentVariable("ARENA_CPU_SENSOR_PIPE");
            if(pipe is not null && System.Text.RegularExpressions.Regex.IsMatch(pipe,@"\AEngineArena\.Cpu\.[0-9]+\.[a-f0-9]{32}\z"))
            {
                try
                {
                    using var client=new NamedPipeClientStream(".",pipe,PipeDirection.In,PipeOptions.Asynchronous);
                    await client.ConnectAsync(250);
                    using var timeout=new CancellationTokenSource(TimeSpan.FromSeconds(4));
                    using var reader=new StreamReader(client);
                    var line=await reader.ReadLineAsync(timeout.Token);
                    using var parsed=JsonDocument.Parse(line??"");
                    Console.WriteLine(parsed.RootElement.GetRawText());
                    return;
                }
                catch(TimeoutException) { /* The session reader has not been enabled. */ }
            }
            var unavailable=CheckDriver();
            if(unavailable is not null){Reply(unavailable);return;}
            var computer=new Computer {IsCpuEnabled=true};
            try {computer.Open();Reply(Sample(computer));}
            finally {computer.Close();}
        }
        catch(Exception ex)
        {
            Reply(new {status="error",message="CPU sensor read failed: "+ex.Message,sensors=Array.Empty<object>()});
        }
    }

    static object? CheckDriver()
    {
            if(!PawnIo.IsInstalled)
            {
                return new {status="driver_missing",message="Install the signed PawnIO sensor driver once to enable CPU temperatures.",sensors=Array.Empty<object>()};
            }
            // Check access first: unsupported driver reads can otherwise appear as zero.
            using(var device=CreateFile(@"\\?\GLOBALROOT\Device\PawnIO",3,3,IntPtr.Zero,3,0,IntPtr.Zero))
            {
                if(device.IsInvalid)
                {
                    int error=Marshal.GetLastWin32Error();
                    return new {status=error==5?"access_denied":"driver_unavailable",message=error==5?"In Hardware display, choose Enable CPU readings for this session and approve the Windows prompt.":"The installed PawnIO driver is not available. Restart Windows or repair the driver installation.",sensors=Array.Empty<object>()};
                }
            }
        return null;
    }

    static object Sample(Computer computer)
    {
        var values=new List<object>();var clocks=new List<object>();
        foreach(var cpu in computer.Hardware.Where(h=>h.HardwareType==HardwareType.Cpu))Read(cpu,cpu.Name,values,clocks);
        return new {status=values.Count+clocks.Count>0?"ok":"unsupported",provider="LibreHardwareMonitor 0.9.6 / PawnIO",driver_version=PawnIo.Version.ToString(),
            message=values.Count+clocks.Count>0?"CPU temperatures and available core clocks read from processor sensors.":"The CPU sensor driver is accessible, but this processor did not provide valid sensor readings.",sensors=values,clocks};
    }

    static async Task Serve(string[] args)
    {
        // Only a fixed CPU-reading operation is elevated: no commands, paths,
        // files or hardware settings are accepted from the unprivileged client.
        using var parent=Process.GetProcessById(int.Parse(args[1]));
        if(parent.StartTime.ToUniversalTime().Ticks!=long.Parse(args[2]) ||
            !Guid.TryParseExact(args[3],"N",out _) || args[5]!="cpu-only" ||
            !string.Equals(parent.MainModule?.FileName,Path.Combine(AppContext.BaseDirectory,"EngineArena.exe"),StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("Invalid Engine Arena session.");
        var sid=new SecurityIdentifier(args[4]);
        _=Task.Run(async()=>{await parent.WaitForExitAsync();Environment.Exit(0);});
        var acl=new PipeSecurity();
        acl.SetAccessRuleProtection(true,false);
        acl.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(WellKnownSidType.NetworkSid,null),PipeAccessRights.FullControl,AccessControlType.Deny));
        acl.AddAccessRule(new PipeAccessRule(sid,PipeAccessRights.Read,AccessControlType.Allow));
        acl.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(WellKnownSidType.BuiltinAdministratorsSid,null),PipeAccessRights.FullControl,AccessControlType.Allow));
        // FirstPipeInstance prevents connecting this elevated reader to a pipe
        // already created by another process. Clients can only read the output.
        using var server=NamedPipeServerStreamAcl.Create($"EngineArena.Cpu.{parent.Id}.{args[3]}",PipeDirection.InOut,1,
            PipeTransmissionMode.Byte,PipeOptions.Asynchronous|PipeOptions.FirstPipeInstance,0,65536,acl);
        var computer=new Computer {IsCpuEnabled=true};
        var unavailable=CheckDriver();
        try
        {
            if(unavailable is null)computer.Open();
            string cached="";long last=0;
            while(!parent.HasExited)
            {
                await server.WaitForConnectionAsync();
                try
                {
                    if(cached.Length==0 || Stopwatch.GetElapsedTime(last).TotalSeconds>=2)
                    {
                        try {cached=JsonSerializer.Serialize(unavailable??Sample(computer));}
                        catch(Exception ex){cached=JsonSerializer.Serialize(new {status="error",message="CPU sensor read failed: "+ex.Message,sensors=Array.Empty<object>()});}
                        last=Stopwatch.GetTimestamp();
                    }
                    using var timeout=new CancellationTokenSource(TimeSpan.FromSeconds(2));
                    await server.WriteAsync(System.Text.Encoding.UTF8.GetBytes(cached+"\n"),timeout.Token);
                    await server.FlushAsync(timeout.Token);
                    // DisconnectNamedPipe discards unread output. Await the
                    // client's close using cancellable overlapped IO instead
                    // of FlushFileBuffers (which can block inside the driver).
                    // The client ACL grants read only; no input is interpreted.
                    if(await server.ReadAsync(new byte[1],timeout.Token)!=0)throw new IOException("Unexpected sensor pipe input.");
                    if(unavailable is not null)return; // Allow a fresh enable after installing/repairing the driver.
                }
                catch(IOException) { /* A reader closing early cannot stop monitoring. */ }
                catch(OperationCanceledException) { /* Bound stalled clients. */ }
                finally {server.Disconnect();}
            }
        }
        finally {computer.Close();}
    }

    static void Read(IHardware hardware,string cpu,List<object> values,List<object> clocks)
    {
        hardware.Update();
        foreach(var sensor in hardware.Sensors)
        {
            if(sensor.Value is not float value || !float.IsFinite(value) || value<=0)continue;
            if(sensor.SensorType==SensorType.Temperature && value<=150)
                values.Add(new {id=sensor.Identifier.ToString(),name=sensor.Name,hardware=cpu,celsius=value});
            // Match individual operating clocks, excluding bus, averages and
            // effective clocks so the maximum always describes a CPU core.
            if(sensor.SensorType==SensorType.Clock && value<=20000 &&
                System.Text.RegularExpressions.Regex.IsMatch(sensor.Name,@"\A(?:CPU )?(?:[PE]-)?Core(?: #[0-9]+)?\z",System.Text.RegularExpressions.RegexOptions.IgnoreCase))
                clocks.Add(new {id=sensor.Identifier.ToString(),name=sensor.Name,hardware=cpu,mhz=value});
        }
        foreach(var child in hardware.SubHardware)Read(child,cpu,values,clocks);
    }
}
