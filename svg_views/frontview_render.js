const rotatiex_compleet = svgmap.rotatiex_compleet.node;
const oplegger2_verplaatsingztext = svgmap.oplegger2_verplaatsingztext_label.node;
const oplegger1_verplaatsingztext = svgmap.oplegger1_verplaatsingztext_label.node;
const oplegger1text = svgmap.oplegger1text_label.node;
const oplegger2text = svgmap.oplegger2text_label.node;
const pijler4_text_compleet = svgmap.pijler4_text_compleet.node;
const pijler5_text_compleet = svgmap.pijler5_text_compleet.node;
const pijler6_text_compleet = svgmap.pijler6_text_compleet.node;

const hoofdpijler4 = svgmap.hoofdpijlergroep.node; 
const aanbrugpijler = svgmap.aanbrugpijlergroep.node;
const basculekelder = svgmap.basculekeldergroep.node;
const hoofdpijler5 = svgmap.hoofdpijler5.node;
const hoofdpijler6 = svgmap.hoofdpijler6.node;
const basculekelder_oplegger2 = svgmap.oplegger2_bascule_geom.node;
const basculekelder_oplegger1 = svgmap.oplegger1_bascule_geom.node;
const opleggingen_aanbrug = svgmap.opleggingen_aanbrug.node;
const opleggingen_pijler4 = svgmap.opleggingen_pijler4.node;
const opleggingen_pijler6 = svgmap.opleggingen_pijler6.node;
const landhoofd = svgmap.landhoofdgroep.node;
const hoofdpijlerlist4 = ["Pijler4"];
const hoofdpijlerlist5 = ["Pijler5"];
const hoofdpijlerlist6 = ["Pijler6"];
const aanbruglist = ["Pijler1", "Pijler2", "Pijler3", "Pijler7", "Pijler8", "Pijler9"];
const basculelist = ["Basculekelder"];
const landhoofdlist = ["LandhoofdZuid", "LandhoofdNoord"];
const bridge_element = data.series[0].fields.find(f => f.name === "Name")?.values?.get(0) ?? "Pijler1"

//Definities van de afstanden tussen de opleggingen & pakken van values
const oplegging_afstand_value = svgmap.oplegging_afstand_value_label.node;
const oplegging_afstand_text = svgmap.oplegging_afstand_text_label.node;
const afstand_compleet = svgmap.afstand_compleet.node;
oplegging_afstand_text.textContent = "Afstand opleggingen "
const brug_opleg_afstand = data.series[0].fields.find(f => f.name === "Brug_opleg_dist")?.values?.get(0) ?? 0;
const hoofd_opleg_afstand = data.series[0].fields.find(f => f.name === "Hoofd_opleg_dist")?.values?.get(0) ?? 0;
const neven_opleg_afstand = data.series[0].fields.find(f => f.name === "Neven_opleg_dist")?.values?.get(0) ?? 0;
const voorhar_opleg_afstand = data.series[0].fields.find(f => f.name === "Voorhar_opleg_dist")?.values?.get(0) ?? 0;

//Definities van de Rotaties
const rotatiex = svgmap.rotatiex_label.node; 
const rotatiextext = svgmap.Rotatiextext_label.node;
const hoofdoplegging_rotatie_compleet = svgmap.hoofdoplegging_rotatie_compleet.node;
const hoofdrotatiex = svgmap.hoofdoplegging_rotatie_value_label.node;;
const brugrotatiex = svgmap.brugoplegging_rotatie_label.node;
const brugoplegging_rotatie = svgmap.brugoplegging_rotatie.node;
const brug_rotatiex_raw = data.series[0].fields.find(f => f.name === "Brug_rotatiex")?.values?.get(0) ?? 0;
const hoofd_rotatiex_raw = data.series[0].fields.find(f => f.name === "Hoofd_rotatiex")?.values?.get(0) ?? 0;
const neven_rotatiex_raw = data.series[0].fields.find(f => f.name === "Neven_rotatiex")?.values?.get(0) ?? 0;

//Definities van de translaties
const oplegger1_verplaatsingz = svgmap.oplegger1_verplaatsingz_label.node;
const oplegger2_verplaatsingz = svgmap.oplegger2_verplaatsingz_label.node;
const oplegger1_verplaatsingz_pijler5 = svgmap.translatiez_value3_5_label.node;
const oplegger2_verplaatsingz_pijler5 = svgmap.translatiez_value4_5_label.node;
const brugoplegger1_verplaatsingz_pijler4 = svgmap.translatiez_brugpunt1_pijler4_label.node;
const brugoplegger2_verplaatsingz_pijler4 = svgmap.translatiez_brugpunt2_pijler4_label.node;
const hoofdoplegger1_verplaatsingz_pijler4 = svgmap.translatiez_hoofdpunt1_pijler4_label.node;
const hoofdoplegger2_verplaatsingz_pijler4 = svgmap.translatiez_hoofdpunt2_pijler4_label.node;
const hoofdoplegger1_verplaatsingz_pijler6 = svgmap.translatiez_punt1_pijler6.node;
const hoofdoplegger2_verplaatsingz_pijler6 = svgmap.translatiez_punt2_pijler6.node;


const brug_deltaz_punt1_raw = data.series[0].fields.find(f => f.name === "Brugpunt1_deltaz")?.values?.get(0) ?? 0;
const brug_deltaz_punt2_raw = data.series[0].fields.find(f => f.name === "Brugpunt2_deltaz")?.values?.get(0) ?? 0;
const hoofd_deltaz_punt1_raw = data.series[0].fields.find(f => f.name === "Hoofdpunt1_deltaz")?.values?.get(0) ?? 0;
const hoofd_deltaz_punt2_raw = data.series[0].fields.find(f => f.name === "Hoofdpunt2_deltaz")?.values?.get(0) ?? 0;


hoofdpijler4.setAttribute("visibility", "hidden");
hoofdpijler5.setAttribute("visibility", "hidden");
hoofdpijler6.setAttribute("visibility", "hidden");
aanbrugpijler.setAttribute("visibility", "hidden");
basculekelder.setAttribute("visibility", "hidden");
basculekelder_oplegger1.setAttribute("visibility", "hidden");
basculekelder_oplegger2.setAttribute("visibility", "hidden");
landhoofd.setAttribute("visibility", "hidden");
opleggingen_aanbrug.setAttribute("visibility", "hidden");
opleggingen_pijler4.setAttribute("visibility", "hidden");
opleggingen_pijler6.setAttribute("visibility", "hidden");
afstand_compleet.removeAttribute("transform");
rotatiex_compleet.removeAttribute("transform")

oplegger1_verplaatsingz.setAttribute("visibility", "visible");
oplegger1_verplaatsingztext.setAttribute("visibility", "visible");
oplegger2_verplaatsingz.setAttribute("visibility", "visible");
oplegger2_verplaatsingztext.setAttribute("visibility", "visible");
oplegger1text.setAttribute("visibility", "visible");
oplegger2text.setAttribute("visibility", "visible");
pijler4_text_compleet.setAttribute("visibility", "hidden");
pijler5_text_compleet.setAttribute("visibility", "hidden");
pijler6_text_compleet.setAttribute("visibility", "hidden")
hoofdoplegging_rotatie_compleet.setAttribute("visibility", "hidden");
brugoplegging_rotatie.setAttribute("visibility", "hidden");
rotatiex.setAttribute("visibility", "visible");
rotatiextext.setAttribute("visibility", "visible");
rotatiex.setAttribute("y", 10);
rotatiextext.setAttribute("y", 10);
oplegging_afstand_value.setAttribute("visibility", "visible");

// Hide element if it's not in the list
if (hoofdpijlerlist4.includes(bridge_element)) {
    hoofdpijler4.setAttribute("visibility", "visible");
    opleggingen_pijler4.setAttribute("visibility", "visible");

    rotatiex_compleet.setAttribute("transform", "translate(70, 0)")
    afstand_compleet.setAttribute("transform", "translate(30, -120)")

    oplegger1_verplaatsingz.setAttribute("visibility", "hidden");
    oplegger1_verplaatsingztext.setAttribute("visibility", "hidden");
    oplegger2_verplaatsingz.setAttribute("visibility", "hidden");
    oplegger2_verplaatsingztext.setAttribute("visibility", "hidden");
    oplegger1text.setAttribute("visibility", "hidden");
    oplegger2text.setAttribute("visibility", "hidden");

    pijler4_text_compleet.setAttribute("visibility", "visible");
    hoofdoplegging_rotatie_compleet.setAttribute("visibility", "visible");
    brugoplegging_rotatie.setAttribute("visibility", "visible");
    rotatiex.setAttribute("visibility", "hidden");
    rotatiextext.setAttribute("visibility", "hidden");

    //Set opleg distance value
    oplegging_afstand_text.textContent = "Afstand Hoofd/Neven opleggingen " + hoofd_opleg_afstand + " m" + " & afstand tussen brug opleggingen " + brug_opleg_afstand + " m"
    oplegging_afstand_value.setAttribute("visibility", "hidden");

    //Set rotation values
    const hoofd_rotatiex_value = Number(hoofd_rotatiex_raw.toFixed(2));
    hoofdrotatiex.textContent = hoofd_rotatiex_value + " mm"
    const brug_rotatiex_value = Number(brug_rotatiex_raw.toFixed(2));
    brugrotatiex.textContent = "Rotatie X-as " + brug_rotatiex_value + " mm"
    const brug_deltaz_punt1_value = Number(brug_deltaz_punt1_raw.toFixed(2));
    const brug_deltaz_punt2_value = Number(brug_deltaz_punt2_raw.toFixed(2));
    const hoofd_deltaz_punt1_value = Number(hoofd_deltaz_punt1_raw.toFixed(2));
    const hoofd_deltaz_punt2_value = Number(hoofd_deltaz_punt2_raw.toFixed(2));
    brugoplegger1_verplaatsingz_pijler4.textContent = brug_deltaz_punt1_value + " mm";
    brugoplegger2_verplaatsingz_pijler4.textContent = brug_deltaz_punt2_value + " mm"
    hoofdoplegger1_verplaatsingz_pijler4.textContent = hoofd_deltaz_punt1_value + " mm"
    hoofdoplegger2_verplaatsingz_pijler4.textContent = hoofd_deltaz_punt2_value + " mm"
    
} else if (hoofdpijlerlist5.includes(bridge_element)) {
    hoofdpijler5.setAttribute("visibility", "visible");

    oplegger1_verplaatsingz.setAttribute("visibility", "hidden");
    oplegger1_verplaatsingztext.setAttribute("visibility", "hidden");
    oplegger2_verplaatsingz.setAttribute("visibility", "hidden");
    oplegger2_verplaatsingztext.setAttribute("visibility", "hidden");
    oplegger1text.setAttribute("visibility", "hidden");
    oplegger2text.setAttribute("visibility", "hidden");

    pijler5_text_compleet.setAttribute("visibility", "visible");
    afstand_compleet.setAttribute("transform", "translate(0,-20)")
    rotatiex_compleet.setAttribute("transform", "translate(60, 80)")

    //Set opleg distance value
    oplegging_afstand_value.textContent = hoofd_opleg_afstand + " m"

    //Set rotation values
    const hoofd_rotatiex_value = Number(hoofd_rotatiex_raw.toFixed(2));
    rotatiex.textContent = hoofd_rotatiex_value + " mm"
    const hoofd_deltaz_punt1_value = Number(hoofd_deltaz_punt1_raw.toFixed(2));
    const hoofd_deltaz_punt2_value = Number(hoofd_deltaz_punt2_raw.toFixed(2));
    oplegger1_verplaatsingz_pijler5.textContent = hoofd_deltaz_punt1_value + " mm"
    oplegger2_verplaatsingz_pijler5.textContent = hoofd_deltaz_punt2_value + " mm"
    
}
 else if (hoofdpijlerlist6.includes(bridge_element)) {
    hoofdpijler6.setAttribute("visibility", "visible");
    opleggingen_pijler6.setAttribute("visibility", "visible");

    oplegger1_verplaatsingz.setAttribute("visibility", "hidden");
    oplegger1_verplaatsingztext.setAttribute("visibility", "hidden");
    oplegger2_verplaatsingz.setAttribute("visibility", "hidden");
    oplegger2_verplaatsingztext.setAttribute("visibility", "hidden");
    oplegger1text.setAttribute("visibility", "hidden");
    oplegger2text.setAttribute("visibility", "hidden");

    pijler6_text_compleet.setAttribute("visibility", "visible");
    afstand_compleet.setAttribute("transform", "translate(0,-100)")
    rotatiex_compleet.setAttribute("transform", "translate(80, 0)")

    //Set opleg distance value
    oplegging_afstand_value.textContent = hoofd_opleg_afstand + " m"

    //Set rotation values
    const hoofd_rotatiex_value = Number(hoofd_rotatiex_raw.toFixed(2));
    rotatiex.textContent = hoofd_rotatiex_value + " mm"
    const hoofd_deltaz_punt1_value = Number(hoofd_deltaz_punt1_raw.toFixed(2));
    const hoofd_deltaz_punt2_value = Number(hoofd_deltaz_punt2_raw.toFixed(2));
    hoofdoplegger1_verplaatsingz_pijler6.textContent = hoofd_deltaz_punt1_value + " mm"
    hoofdoplegger2_verplaatsingz_pijler6.textContent = hoofd_deltaz_punt2_value + " mm"
}
else if (aanbruglist.includes(bridge_element)) {
    aanbrugpijler.setAttribute("visibility", "visible");
    opleggingen_aanbrug.setAttribute("visibility", "visible");
    rotatiex.setAttribute("y", 160);
    rotatiextext.setAttribute("y", 160);
    oplegger1_verplaatsingz.setAttribute("y", 260);
    oplegger1_verplaatsingz.setAttribute("x", 100);
    oplegger1_verplaatsingztext.setAttribute("y", 230);
    oplegger1_verplaatsingztext.setAttribute("x", 100);
    oplegger1text.setAttribute("x", 100);
    oplegger1text.setAttribute("y", 200);
    oplegger2text.setAttribute("x", 920);
    oplegger2text.setAttribute("y", 200);
    oplegger2_verplaatsingztext.setAttribute("x", 920);
    oplegger2_verplaatsingztext.setAttribute("y", 230);
    oplegger2_verplaatsingz.setAttribute("y", 260);
    oplegger2_verplaatsingz.setAttribute("x", 920);
    oplegging_afstand_value.textContent = brug_opleg_afstand + " m"

    afstand_compleet.setAttribute("transform", "translate(0,20)")
    rotatiex_compleet.setAttribute("transform", "translate(70, -20)")

    const brug_rotatiex_value = Number(brug_rotatiex_raw.toFixed(2));
    rotatiex.textContent = brug_rotatiex_value + " mm"
    const brug_deltaz_punt1_value =  Number(brug_deltaz_punt1_raw.toFixed(2));
    oplegger1_verplaatsingz.textContent = brug_deltaz_punt1_value + " mm" 
    const brug_deltaz_punt2_value =  Number(brug_deltaz_punt2_raw.toFixed(2));
    oplegger2_verplaatsingz.textContent = brug_deltaz_punt2_value + " mm" 

} else if (basculelist.includes(bridge_element)) {
    basculekelder.setAttribute("visibility", "visible");
    basculekelder_oplegger1.setAttribute("visibility", "visible");
    basculekelder_oplegger2.setAttribute("visibility", "visible");

    oplegger1_verplaatsingz.setAttribute("y", 241.5);
    oplegger1_verplaatsingz.setAttribute("x", 234.74);
    oplegger1_verplaatsingztext.setAttribute("y", 210);
    oplegger1_verplaatsingztext.setAttribute("x", 234.74);
    oplegger1text.setAttribute("x", 234.74);
    oplegger1text.setAttribute("y", 145);

    oplegger2text.setAttribute("x", 785);
    oplegger2text.setAttribute("y", 140);
    oplegger2_verplaatsingztext.setAttribute("x", 785);
    oplegger2_verplaatsingztext.setAttribute("y", 210);
    oplegger2_verplaatsingz.setAttribute("y", 241.5);
    oplegger2_verplaatsingz.setAttribute("x", 785);

    rotatiex.setAttribute("y", 10);
    rotatiextext.setAttribute("y", 10);
    rotatiex_compleet.setAttribute("transform", "translate(50, 0)")
    oplegging_afstand_value.textContent = brug_opleg_afstand + " m"

    const brug_rotatiex_value = Number(brug_rotatiex_raw.toFixed(2));
    rotatiex.textContent = brug_rotatiex_value + " mm"
    const brug_deltaz_punt1_value =  Number(brug_deltaz_punt1_raw.toFixed(2));
    oplegger1_verplaatsingz.textContent = brug_deltaz_punt1_value + " mm" 
    const brug_deltaz_punt2_value =  Number(brug_deltaz_punt2_raw.toFixed(2));
    oplegger2_verplaatsingz.textContent = brug_deltaz_punt2_value + " mm" 

} else if (landhoofdlist.includes(bridge_element)) {
    aanbrugpijler.setAttribute("visibility", "visible");
    opleggingen_aanbrug.setAttribute("visibility", "visible");
    rotatiex.setAttribute("y", 160);
    rotatiextext.setAttribute("y", 160);
    oplegger1_verplaatsingz.setAttribute("y", 260);
    oplegger1_verplaatsingz.setAttribute("x", 100);
    oplegger1_verplaatsingztext.setAttribute("y", 230);
    oplegger1_verplaatsingztext.setAttribute("x", 100);
    oplegger1text.setAttribute("x", 100);
    oplegger1text.setAttribute("y", 200);
    oplegger2text.setAttribute("x", 920);
    oplegger2text.setAttribute("y", 200);
    oplegger2_verplaatsingztext.setAttribute("x", 920);
    oplegger2_verplaatsingztext.setAttribute("y", 230);
    oplegger2_verplaatsingz.setAttribute("y", 260);
    oplegger2_verplaatsingz.setAttribute("x", 920);
    oplegging_afstand_value.textContent = brug_opleg_afstand + " m"

    afstand_compleet.setAttribute("transform", "translate(0,20)")
    rotatiex_compleet.setAttribute("transform", "translate(70, -20)")

    const brug_rotatiex_value = Number(brug_rotatiex_raw.toFixed(2));
    rotatiex.textContent = brug_rotatiex_value + " mm"
    const brug_deltaz_punt1_value =  Number(brug_deltaz_punt1_raw.toFixed(2));
    oplegger1_verplaatsingz.textContent = brug_deltaz_punt1_value + " mm" 
    const brug_deltaz_punt2_value =  Number(brug_deltaz_punt2_raw.toFixed(2));
    oplegger2_verplaatsingz.textContent = brug_deltaz_punt2_value + " mm" 
}