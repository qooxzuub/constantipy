from hypothesis import given, strategies as st
from constantipy.heuristics import generate_name

# Strategy for text: anything except null bytes
clean_text = st.text().filter(lambda x: "\x00" not in x)


@given(val=clean_text, idx=st.integers(min_value=0))
def test_fuzz_generate_name_str(val, idx):
    """Fuzzes string inputs to ensure generate_name always produces valid Python identifiers."""
    name = generate_name(val, "derived", idx)

    assert isinstance(name, str)
    assert len(name) > 0
    # Check it doesn't start with a digit
    assert not name[0].isdigit()

    # If it's not a generic fallback like "STR_CONST_1", it should be a valid identifier
    # (Generic fallbacks are also valid identifiers, but this checks the derived logic)
    if not name.startswith("STR_CONST"):
        assert name.isidentifier()


@given(val=st.integers(), idx=st.integers(min_value=0))
def test_fuzz_generate_name_int(val, idx):
    """Fuzzes integer inputs to ensure generate_name produces valid INT constants."""
    name = generate_name(val, "derived", idx)
    assert name.startswith("INT_") or "NEG_" in name
    assert name.isidentifier()


@given(
    val=st.floats(allow_nan=False, allow_infinity=False), idx=st.integers(min_value=0)
)
def test_fuzz_generate_name_float(val, idx):
    """Fuzzes float inputs to ensure generate_name produces valid FLOAT constants."""
    name = generate_name(val, "derived", idx)
    assert name.startswith("FLOAT_")
    assert name.isidentifier()


@given(val=st.binary(), idx=st.integers(min_value=0))
def test_fuzz_generate_name_bytes(val, idx):
    """Fuzzes bytes inputs."""
    name = generate_name(val, "derived", idx)
    assert name.startswith("BYTES_")
    assert name.isidentifier()
