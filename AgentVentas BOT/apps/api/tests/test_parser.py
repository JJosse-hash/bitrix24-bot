from address_ai.core.parser import MexicanAddressParser


def test_parse_call_example():
    parsed = MexicanAddressParser().parse(
        "Estoy por San Nicolás, enfrente de un panteón, la calle creo que se llama Abedul, entre Sauce y otra calle, y la casa es la 137."
    )
    assert parsed.state.value == "Nuevo León"
    assert parsed.municipality.value == "San Nicolás de los Garza"
    assert parsed.house_number.value == "137"
    assert "cementerio" in [item.value for item in parsed.poi_categories]
    assert parsed.streets[0].value == "Abedul"


def test_parse_non_conventional_address():
    parsed = MexicanAddressParser().parse("MZ 4 LT 18 COL SAN JOSE atras de la iglesia")
    assert parsed.block.value == "4"
    assert parsed.lot.value == "18"
    assert "iglesia" in [item.value for item in parsed.poi_categories]


def test_parse_intersection_and_postal_code():
    parsed = MexicanAddressParser().parse("AV JUAREZ #120 entre Juarez y Morelos CP 64000")
    assert parsed.house_number.value == "120"
    assert parsed.postal_code.value == "64000"
    assert len(parsed.intersections) == 2
