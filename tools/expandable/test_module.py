import NeuraDemo
import NeuraDemoAchive
import pytest

@pytest.mark.parametrize("module", [NeuraDemoAchive, NeuraDemo])
def test_core_functionality(module):
    input_data = {...}  # 你的输入数据

    # 设置输出目录
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # 执行模块功能
    log_path = output_dir / "trace.log"
    module.generate_trace(input_data, output_path=log_path)

    # 如果是第一个模块(原始模块)，保存结果作为预期
    if module == original_module:
        expected_log = log_path.read_text()
    else:
        # 比较重构后模块生成的日志与原始日志
        current_log = log_path.read_text()
        assert current_log == expected_log, "重构后生成的trace.log内容与原始版本不一致"

@pytest.fixture
def expected_results():
    # 记录原始脚本在各种输入下的正确输出
    return {
        "test_case_1": original_module.process(input_1),
        "test_case_2": original_module.process(input_2),
        # ...
    }

def test_refactored_against_baseline(refactored_module, expected_results):
    for name, expected in expected_results.items():
        input_data = get_input_for_test_case(name)
        assert refactored_module.process(input_data) == expected

