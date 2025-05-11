import importlib
import sys

def check_module_version(module_name):
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, '__version__', 'Không rõ')
        print(f"{module_name}: {version}")
    except ImportError:
        print(f"{module_name}: Chưa cài đặt")

def check_gpu():
    try:
        import pynvml
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        print(f"Số lượng GPU: {device_count}")
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode('utf-8')
            print(f"  GPU {i}: {name}")
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            print(f"  Bộ nhớ: {mem.total // (1024**2)} MB")
        pynvml.nvmlShutdown()
    except ImportError:
        print("pynvml: Chưa cài đặt (pip install pynvml)")
    except Exception as e:
        print(f"Lỗi kiểm tra GPU: {e}")

def check_cuda_version():   
    try:
        import cupy
        print(f"CUDA version (cupy): {cupy.cuda.runtime.runtimeGetVersion()}")
    except ImportError:
        print("cupy: Chưa cài đặt")

if __name__ == "__main__":
    print("=== Kiểm tra GPU ===")
    check_gpu()
    print("\n=== Kiểm tra phiên bản CUDA ===")
    check_cuda_version()
    print("\n=== Kiểm tra phiên bản RAPIDS ===")
    for lib in ["cudf", "cuml", "cugraph", "cuspatial", "cupy", "rmm"]:
        check_module_version(lib)
