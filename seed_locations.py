"""Seed initial Yemeni governorates and common districts."""

from app.database import SessionLocal
from app.models import District, Governorate


LOCATIONS = [
    (
        "أمانة العاصمة",
        "Sana'a City",
        [
            ("السبعين", "Al Sabain"),
            ("التحرير", "Al Tahrir"),
            ("معين", "Maain"),
            ("شعوب", "Shuub"),
            ("آزال", "Azal"),
            ("الصافية", "Al Safiyah"),
            ("الوحدة", "Al Wahdah"),
            ("الثورة", "Al Thawrah"),
            ("بني الحارث", "Bani Al Harith"),
            ("صنعاء القديمة", "Old Sana'a"),
        ],
    ),
    (
        "صنعاء",
        "Sana'a",
        [
            ("سنحان وبني بهلول", "Sanhan and Bani Bahlul"),
            ("بني حشيش", "Bani Hushaysh"),
            ("همدان", "Hamdan"),
            ("أرحب", "Arhab"),
            ("نهم", "Nihm"),
            ("بلاد الروس", "Bilad Ar Rus"),
            ("الحيمة الداخلية", "Al Haymah Ad Dakhiliyah"),
            ("الحيمة الخارجية", "Al Haymah Al Kharijiyah"),
            ("مناخة", "Manakhah"),
            ("بني مطر", "Bani Matar"),
            ("خولان", "Khawlan"),
        ],
    ),
    (
        "عدن",
        "Aden",
        [
            ("كريتر", "Crater"),
            ("المعلا", "Al Mualla"),
            ("التواهي", "Al Tawahi"),
            ("خور مكسر", "Khormaksar"),
            ("المنصورة", "Al Mansurah"),
            ("الشيخ عثمان", "Sheikh Othman"),
            ("دار سعد", "Dar Saad"),
            ("البريقة", "Al Buraiqah"),
        ],
    ),
    (
        "تعز",
        "Taiz",
        [
            ("القاهرة", "Al Qahirah"),
            ("المظفر", "Al Mudhaffar"),
            ("صالة", "Salah"),
            ("التعزية", "At Taiziyah"),
            ("ماوية", "Mawiyah"),
            ("الشمايتين", "Ash Shamayatayn"),
            ("جبل حبشي", "Jabal Habashy"),
            ("المخا", "Al Mukha"),
            ("الوازعية", "Al Waziiyah"),
            ("صبر الموادم", "Sabir Al Mawadim"),
            ("المسراخ", "Al Misrakh"),
            ("خدير", "Khadeer"),
        ],
    ),
    (
        "إب",
        "Ibb",
        [
            ("الظهار", "Al Dhihar"),
            ("المشنة", "Al Mashannah"),
            ("جبلة", "Jiblah"),
            ("بعدان", "Baadan"),
            ("يريم", "Yarim"),
            ("النادرة", "An Nadirah"),
            ("العدين", "Al Udayn"),
            ("فرع العدين", "Far Al Udayn"),
            ("حبيش", "Hubaysh"),
            ("القفر", "Al Qafr"),
        ],
    ),
    (
        "الحديدة",
        "Al Hudaydah",
        [
            ("الحوك", "Al Hawak"),
            ("الحالي", "Al Hali"),
            ("الميناء", "Al Mina"),
            ("بيت الفقيه", "Bayt Al Faqih"),
            ("زبيد", "Zabid"),
            ("باجل", "Bajil"),
            ("اللحية", "Al Luhayyah"),
            ("القناوص", "Al Qanawis"),
            ("الدريهمي", "Ad Durayhimi"),
            ("التحيتا", "At Tuhayta"),
        ],
    ),
    (
        "حضرموت",
        "Hadramout",
        [
            ("المكلا", "Al Mukalla"),
            ("الشحر", "Ash Shihr"),
            ("سيئون", "Seiyun"),
            ("تريم", "Tarim"),
            ("القطن", "Al Qatn"),
            ("شبام", "Shibam"),
            ("غيل باوزير", "Ghayl Ba Wazir"),
            ("وادي العين وحورة", "Wadi Al Ayn and Hawrah"),
            ("دوعن", "Daw'an"),
        ],
    ),
    (
        "لحج",
        "Lahj",
        [
            ("الحوطة", "Al Hawtah"),
            ("تبن", "Tuban"),
            ("ردفان", "Radfan"),
            ("طور الباحة", "Tur Al Bahah"),
            ("المقاطرة", "Al Maqatirah"),
            ("المسيمير", "Al Musaymir"),
            ("يافع", "Yafa"),
        ],
    ),
    (
        "أبين",
        "Abyan",
        [
            ("زنجبار", "Zinjibar"),
            ("خنفر", "Khanfar"),
            ("لودر", "Lawdar"),
            ("مودية", "Mudiyah"),
            ("المحفد", "Al Mahfad"),
            ("جيشان", "Jayshan"),
        ],
    ),
    (
        "شبوة",
        "Shabwah",
        [
            ("عتق", "Ataq"),
            ("بيحان", "Bayhan"),
            ("عسيلان", "Usaylan"),
            ("ميفعة", "Mayfaah"),
            ("نصاب", "Nisab"),
            ("حبان", "Habban"),
            ("الروضة", "Ar Rawdah"),
        ],
    ),
    (
        "مأرب",
        "Marib",
        [
            ("مدينة مأرب", "Marib City"),
            ("الوادي", "Al Wadi"),
            ("حريب", "Harib"),
            ("الجوبة", "Al Jubah"),
            ("صرواح", "Sirwah"),
            ("رغوان", "Raghwan"),
        ],
    ),
    (
        "ذمار",
        "Dhamar",
        [
            ("مدينة ذمار", "Dhamar City"),
            ("عنس", "Ans"),
            ("ميفعة عنس", "Mayfa'at Ans"),
            ("عتمة", "Utmah"),
            ("وصاب العالي", "Wusab Al Ali"),
            ("وصاب السافل", "Wusab As Safil"),
            ("جهران", "Jahran"),
        ],
    ),
    (
        "البيضاء",
        "Al Bayda",
        [
            ("البيضاء", "Al Bayda"),
            ("رداع", "Rada'a"),
            ("مكيراس", "Mukayras"),
            ("السوادية", "As Sawadiyah"),
            ("القريشية", "Al Quraishyah"),
            ("ذي ناعم", "Dhi Na'im"),
            ("الصومعة", "As Sawma'ah"),
        ],
    ),
    (
        "صعدة",
        "Saada",
        [
            ("صعدة", "Saada"),
            ("سحار", "Sahar"),
            ("ساقين", "Saqayn"),
            ("رازح", "Razih"),
            ("غمر", "Ghamr"),
            ("كتاف والبقع", "Kitaf and Al Buqa"),
            ("مجز", "Majz"),
        ],
    ),
    (
        "حجة",
        "Hajjah",
        [
            ("مدينة حجة", "Hajjah City"),
            ("عبس", "Abs"),
            ("كشر", "Kushar"),
            ("مستبأ", "Mustaba"),
            ("المحابشة", "Al Mahabishah"),
            ("حرض", "Haradh"),
            ("ميدي", "Midi"),
        ],
    ),
    (
        "عمران",
        "Amran",
        [
            ("عمران", "Amran"),
            ("خمر", "Khamir"),
            ("حوث", "Huth"),
            ("حرف سفيان", "Harf Sufyan"),
            ("ريدة", "Raydah"),
            ("شهارة", "Shaharah"),
            ("ثلا", "Thula"),
        ],
    ),
    (
        "الجوف",
        "Al Jawf",
        [
            ("الحزم", "Al Hazm"),
            ("برط العنان", "Bart Al Anan"),
            ("خب والشعف", "Khab wa Ash Sha'af"),
            ("المتون", "Al Matun"),
            ("المصلوب", "Al Maslub"),
            ("الغيل", "Al Ghayl"),
        ],
    ),
    (
        "المهرة",
        "Al Mahrah",
        [
            ("الغيضة", "Al Ghaydah"),
            ("شحن", "Shahan"),
            ("سيحوت", "Sayhut"),
            ("قشن", "Qishn"),
            ("حوف", "Hawf"),
            ("المسيلة", "Al Masilah"),
        ],
    ),
    (
        "المحويت",
        "Al Mahwit",
        [
            ("المحويت", "Al Mahwit"),
            ("شبام كوكبان", "Shibam Kawkaban"),
            ("الطويلة", "At Tawilah"),
            ("الخبت", "Al Khabt"),
            ("الرجم", "Ar Rujum"),
            ("ملحان", "Milhan"),
        ],
    ),
    (
        "ريمة",
        "Raymah",
        [
            ("الجبين", "Al Jabin"),
            ("كسمة", "Kusmah"),
            ("السلفية", "As Salafiyah"),
            ("بلاد الطعام", "Bilad At Taam"),
            ("مزهر", "Mazhar"),
        ],
    ),
    (
        "الضالع",
        "Al Dhale'e",
        [
            ("الضالع", "Al Dhale'e"),
            ("دمت", "Damt"),
            ("قعطبة", "Qa'atabah"),
            ("الحصين", "Al Husayn"),
            ("الشعيب", "Ash Shu'ayb"),
            ("الأزارق", "Al Azariq"),
        ],
    ),
    (
        "سقطرى",
        "Socotra",
        [
            ("حديبو", "Hadibu"),
            ("قلنسية وعبد الكوري", "Qulansiyah and Abd Al Kuri"),
        ],
    ),
]


def seed():
    db = SessionLocal()
    governorates_added = 0
    districts_added = 0
    try:
        for name_ar, name_en, districts in LOCATIONS:
            governorate = db.query(Governorate).filter(Governorate.name_ar == name_ar).first()
            if governorate is None:
                governorate = Governorate(name_ar=name_ar, name_en=name_en, is_active=True)
                db.add(governorate)
                db.flush()
                governorates_added += 1
            else:
                governorate.name_en = name_en
                governorate.is_active = True

            for district_ar, district_en in districts:
                exists = (
                    db.query(District)
                    .filter(
                        District.governorate_id == governorate.id,
                        District.name_ar == district_ar,
                    )
                    .first()
                )
                if exists is not None:
                    exists.name_en = district_en
                    exists.is_active = True
                    continue

                db.add(
                    District(
                        governorate_id=governorate.id,
                        name_ar=district_ar,
                        name_en=district_en,
                        is_active=True,
                    )
                )
                districts_added += 1

        db.commit()
        print(f"Added governorates: {governorates_added}")
        print(f"Added districts: {districts_added}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
